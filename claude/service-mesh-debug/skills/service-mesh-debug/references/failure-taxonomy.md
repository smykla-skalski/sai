# Universal Service Mesh Failure Taxonomy

Every service mesh failure — regardless of implementation — falls into one of these six categories.
Use this to rapidly classify a reported issue before diving into mesh-specific commands.

# Contents

- [Category 1: Control Plane Connectivity](#category-1-control-plane-connectivity)
- [Category 2: Proxy / Sidecar Lifecycle](#category-2-proxy--sidecar-lifecycle)
- [Category 3: mTLS / Certificate / Identity](#category-3-mtls--certificate--identity)
- [Category 4: Traffic Routing / Policy](#category-4-traffic-routing--policy)
- [Category 5: Service Discovery / Endpoint Resolution](#category-5-service-discovery--endpoint-resolution)
- [Category 6: Infrastructure / Platform](#category-6-infrastructure--platform)
- [Failure Category Quick Reference](#failure-category-quick-reference)

---

## Category 1: Control Plane Connectivity

The proxy cannot reach the control plane, or the control plane is unhealthy.

**Signals:**
- `control_plane.connected_state = 0` (Envoy admin stats)
- Proxy has very old config version (no updates for minutes/hours)
- Control plane pod crash-looping or OOM-killed
- All proxies simultaneously start misbehaving (systemic, not single-pod)

**Diagnosis:**
```bash
# Kuma
kubectl get pod -n kuma-system
kubectl logs -n kuma-system deploy/kuma-control-plane --tail=50
kubectl exec <pod> -c kuma-sidecar -- wget -qO- 'localhost:9901/stats?filter=control_plane'

# Istio
kubectl get pod -n istio-system -lapp=istiod
kubectl logs -n istio-system deploy/istiod --tail=50
istioctl proxy-status  # shows STALE/NOT_SENT columns
```

**Common causes:**
- Network policy blocking proxy → CP port
- CP resource exhaustion (CPU/memory limits too tight)
- Version skew between CLI, CP, and data plane proxies
- CP pod evicted due to node pressure

---

## Category 2: Proxy / Sidecar Lifecycle

The proxy is absent, not ready, or has the wrong version.

**Signals:**
- Pod has no sidecar container (traffic bypasses the mesh entirely)
- Pod starts failing immediately after namespace labeled for injection
- App gets `connection refused` on startup (app starts before proxy ready)
- New mesh version deployed; some proxies not upgraded

**Diagnosis:**
```bash
# Is sidecar present?
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].name}'

# Kuma — check injection annotation
kubectl get pod <pod> -o jsonpath='{.metadata.annotations.kuma\.io/sidecar-injection}'

# Istio — why did/didn't injection fire?
istioctl experimental check-inject -n <ns> <pod>

# Linkerd — check annotation
kubectl get pod <pod> -o jsonpath='{.metadata.annotations.linkerd\.io/inject}'

# Proxy version vs CP version
kubectl exec <pod> -c kuma-sidecar -- wget -qO- localhost:9901/server_info | jq .version
```

**Common causes:**
- Namespace missing injection label (`kuma.io/mesh`, `istio-injection=enabled`, `linkerd.io/inject=enabled`)
- Pod has explicit opt-out annotation
- Admission webhook not running (CP down at pod creation time)
- `hostNetwork: true` on pod (injection skipped — can't intercept)

---

## Category 3: mTLS / Certificate / Identity

TLS handshake fails, connections rejected, or wrong identity presented.

**Signals:**
- `ssl.connection_error`, `ssl.fail_verify_error`, `ssl.fail_verify_san` in Envoy stats
- `SSLV3_ALERT_HANDSHAKE_FAILURE` in transport failure reason
- `Secret is not supplied by SDS` — cert not yet delivered to proxy
- `upstream_reset_before_response_started{connection_failure}` in access logs
- mTLS works for established pods but fails for newly started ones

**Diagnosis:**
```bash
# Cert expiry (any Envoy-based mesh)
kubectl exec <pod> -c kuma-sidecar -- wget -qO- localhost:9901/certs | \
  jq '.certificates[].cert_chain[].days_until_expiration'

# SDS delivery status (warming = not yet delivered)
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/config_dump?resource=dynamic_warming_secrets'

# Istio — SPIFFE identity in cert
istioctl proxy-config secret <pod>.<ns>

# TLS error stats
kubectl exec <pod> -c kuma-sidecar -- wget -qO- 'localhost:9901/stats?filter=ssl'

# See scripts/mtls_check.py for automated check
```

**Common causes:**
- Newly started pod: leaf cert not yet delivered by SDS (takes 2–30s depending on load)
- Root CA expired (silent — new certs signed by expired CA fail verification)
- mTLS mode mismatch: one side expects plaintext, other sends TLS
- Istio: PeerAuthentication STRICT with no matching DestinationRule → 503
- Clock skew >5 minutes causes cert validity checks to fail

---

## Category 4: Traffic Routing / Policy

Traffic is blocked by authorization policy, or routes to the wrong destination.

**Signals:**
- `UAEX` response flag (denied by ext-authz / policy)
- `NR` response flag (no route configured)
- 403/404 from the mesh, not from the app
- Traffic worked before mesh was enabled, fails after
- Partial traffic block (some source/destination pairs fail, others succeed)

**Diagnosis:**
```bash
# Kuma — which policies apply?
kumactl inspect dataplane <name> --mesh default

# Istio — authorization policies as Envoy sees them
istioctl x authz check <pod>.<ns>
# Enable RBAC debug:
istioctl proxy-config log deploy/<app> --level "rbac:debug"
kubectl logs deploy/<app> -c istio-proxy | grep -E "enforced|shadow"

# Consul
consul-k8s troubleshoot upstreams -pod <pod>
```

**Common causes:**
- Default-deny: mesh now blocks traffic that previously flowed freely
- Kuma: first MeshTrafficPermission created activates policy evaluation (implicit deny-all for unmatched)
- Istio: any ALLOW policy creates implicit deny-all for non-matching traffic
- Istio AuthorizationPolicy YAML: list items under a single rule are OR, not AND
- DENY policy always beats ALLOW regardless of order
- Policy applied but not yet propagated to proxy (see Category 5)

---

## Category 5: Service Discovery / Endpoint Resolution

The proxy knows about the service but can't find healthy backends.

**Signals:**
- `UH` response flag (no healthy upstream hosts)
- `membership_healthy = 0` in Envoy cluster stats
- `ejections_active > 0` (outlier detection ejected all hosts)
- Requests succeed to some replicas but not others (partial endpoint failure)

**Diagnosis:**
```bash
# Envoy cluster health (any mesh)
kubectl exec <pod> -c kuma-sidecar -- wget -qO- localhost:9901/clusters | \
  grep -E 'health_flags|membership_healthy|membership_total'

# Outlier ejection
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=outlier_detection.ejections_active'

# Circuit breaker open
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=circuit_breakers.default.cx_open'

# Istio — endpoint IPs per cluster
istioctl proxy-config endpoint <pod>.<ns>
# Compare to actual pod IPs:
kubectl get pod -l app=<name> -o wide
```

**Common causes:**
- Health check misconfigured (all hosts fail checks → `UH`)
- Outlier detection ejected hosts after fault injection test (30s base ejection time)
- Circuit breaker tripped under load (`UO` flag) — Envoy defaults: 1024 max requests, 3 retries
- Pod restarted; stale endpoint IP still cached in routing table
- Service not registered in mesh (no dataplane resource / service entry)

---

## Category 6: Infrastructure / Platform

Infrastructure problems that manifest as mesh failures.

**Signals:**
- Multiple unrelated mesh features broken simultaneously
- Failures correlated with node or zone (not service)
- Problems appear after cluster upgrade, node replacement, or cert rotation
- Admission webhook timeouts during pod creation

**Diagnosis:**
```bash
# Node clock skew
kubectl get nodes -o json | jq '.items[].status.conditions[] | select(.type=="Ready") | {node: .metadata, reason: .reason}'
# Check NTP sync on nodes

# RBAC for control plane
kubectl auth can-i list pods --as=system:serviceaccount:kuma-system:kuma-control-plane

# Webhook status
kubectl get validatingwebhookconfigurations,mutatingwebhookconfigurations | grep kuma

# Resource exhaustion on sidecar
kubectl top pod <pod> --containers
kubectl describe pod <pod> | grep -A5 "Limits:"
```

**Common causes:**
- Network policy blocking mesh control plane traffic (common in strict enterprise clusters)
- CPU limits too tight on sidecar → proxy can't handle load → timeouts
- RBAC missing: CP can't read/write needed K8s resources
- Clock drift >5 minutes breaking cert validity (especially after node replacement)
- K8s API server slow → admission webhook timeouts → pod creation stalls

---

## Failure Category Quick Reference

| Symptom | Most likely category |
|---------|---------------------|
| All pods broken simultaneously | 1 (Control Plane) |
| Single pod no sidecar | 2 (Lifecycle) |
| `Secret is not supplied by SDS` | 3 (Certificates) |
| TLS handshake failure | 3 (Certificates) |
| 403 / `UAEX` flag | 4 (Policy) |
| Traffic worked before mesh, broken after | 4 (Policy) |
| `UH` / no healthy hosts | 5 (Service Discovery) |
| Circuit breaker / `UO` flag | 5 (Service Discovery) |
| Works on some nodes, not others | 6 (Infrastructure) |
| Problems after node replacement | 6 (Infrastructure) |
| Flaky in CI, passes locally | 1 or 3 (CP load / cert delivery timing) |
