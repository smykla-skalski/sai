# Universal Service Mesh Debugging Workflow

Applies to Kuma, Istio, Linkerd, and Consul Connect. Debug in phase order — each phase
gates the next. Jumping to phase 6 when phase 2 is the problem wastes time.

# Contents

- [7-Phase Debugging Workflow](#7-phase-debugging-workflow)
  - [Phase 1: Is the mesh control plane healthy?](#phase-1-is-the-mesh-control-plane-healthy)
  - [Phase 2: Is the workload enrolled in the mesh?](#phase-2-is-the-workload-enrolled-in-the-mesh)
  - [Phase 3: Is the proxy synced with the control plane?](#phase-3-is-the-proxy-synced-with-the-control-plane)
  - [Phase 4: Are certificates valid?](#phase-4-are-certificates-valid)
  - [Phase 5: Is there a policy allowing this traffic?](#phase-5-is-there-a-policy-allowing-this-traffic)
  - [Phase 6: Is routing configured correctly?](#phase-6-is-routing-configured-correctly)
  - [Phase 7: Examine live traffic](#phase-7-examine-live-traffic)
- [Cross-Mesh CLI Quick Reference](#cross-mesh-cli-quick-reference)
- [Flaky E2E Test Patterns (Universal Across Meshes)](#flaky-e2e-test-patterns-universal-across-meshes)

---

## 7-Phase Debugging Workflow

### Phase 1: Is the mesh control plane healthy?

Run the mesh's native health check first. This catches the majority of "mysterious" failures.

| Mesh | Command |
|------|---------|
| Kuma | `kumactl get zones` + `kubectl get pod -n kuma-system` |
| Istio | `istioctl analyze -n <namespace>` |
| Linkerd | `linkerd check` |
| Consul | `consul-k8s status` |

Also check: control plane pod restarts, OOM kills, resource exhaustion.

---

### Phase 2: Is the workload enrolled in the mesh?

A pod that isn't in the mesh won't get mTLS, policies, or traffic management.

```bash
# Kuma — is the dataplane registered?
kumactl get dataplanes --mesh default | grep <pod-name>
# or check kuma-sidecar container presence:
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].name}'

# Istio — sidecar injected?
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].name}' | tr ' ' '\n' | grep istio-proxy
# Why did/didn't injection happen?
istioctl experimental check-inject -n <ns> <pod>

# Linkerd
kubectl get pod <pod> -o jsonpath='{.spec.initContainers[*].name}' | grep linkerd
linkerd check --proxy -n <ns>
```

Injection is controlled by namespace labels and pod annotations. Check both:
```bash
kubectl get ns <ns> --show-labels
kubectl get pod <pod> -o jsonpath='{.metadata.annotations}'
```

---

### Phase 3: Is the proxy synced with the control plane?

A proxy with stale config silently uses old routing/policy decisions.

```bash
# Kuma — connected and latest config?
kumactl get dataplanes --mesh default -o json | \
  jq '.items[] | select(.metadata.name | contains("<name>")) | .status'
# Envoy-level sync:
kubectl exec <pod> -c kuma-sidecar -- wget -qO- 'localhost:9901/stats?filter=control_plane'
# control_plane.connected_state = 1 (good), 0 (disconnected)

# Istio — full sync status across all proxies
istioctl proxy-status
# SYNCED = good, STALE = received update but hasn't acked, NOT SENT = istiod hasn't pushed
# Per-pod config diff (what istiod sent vs what Envoy loaded):
istioctl proxy-status <pod>.<ns>

# Linkerd
linkerd diagnostics endpoints <service>.<ns>:port
```

If proxy shows STALE or disconnected → check control plane logs for push errors.

---

### Phase 4: Are certificates valid?

Certificate problems are the #1 operational surprise in service meshes. Check:
1. Root CA expiry
2. Intermediate CA expiry (if present)
3. Leaf cert expiry on the specific pod
4. Trust chain — cert issued by the configured trust anchor
5. Clock skew (Linkerd tolerates ≤5 min; others vary)

```bash
# Kuma / any Envoy-based mesh — cert expiry via admin API
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- localhost:9901/certs | jq '.certificates[].cert_chain[].days_until_expiration'
# See also scripts/mtls_check.py

# Istio — includes SPIFFE SAN verification
istioctl proxy-config secret <pod>.<ns>
# Shows: cert name, type, issuer, expiry, SAN

# Linkerd
linkerd check  # identity section checks cert expiry
linkerd diagnostics policy -n <ns> <pod>:port

# Check root CA expiry (Kuma)
kubectl get secret -n kuma-system kuma-tls-cert -o jsonpath='{.data.tls\.crt}' | \
  base64 -d | openssl x509 -noout -dates
```

If certs are expired or rotating: wait for rotation to complete, or force restart of the sidecar.

---

### Phase 5: Is there a policy allowing this traffic?

All meshes default-deny traffic once authorization is enabled. Check whether a policy
explicitly allows the source → destination pair.

```bash
# Kuma — which policies apply?
kumactl inspect dataplane <name> --mesh default
kumactl get meshtrafficpermissions --mesh default
kumactl get meshtcproutes --mesh default

# Istio — merged AuthorizationPolicy as Envoy sees it
istioctl x authz check <pod>.<ns>
# Enable RBAC debug logging:
istioctl proxy-config log deploy/<app> --level "rbac:debug"
kubectl logs deploy/<app> -c istio-proxy | grep "enforced"
# "enforced allowed, matched policy: <name>" or "enforced denied, no matched policy found"

# Consul
consul-k8s troubleshoot upstreams -pod <pod>
consul-k8s troubleshoot proxy -pod <pod>

# Linkerd — mTLS is automatic; check server authorization
kubectl get serverauthorization,server -n <ns>
```

**Common policy mistakes:**
- Kuma: missing `MeshTrafficPermission` (default deny after first policy is applied)
- Istio: any ALLOW policy makes all non-matching traffic DENIED (implicit deny-all side effect)
- Istio: YAML `-` list items = OR logic, not AND — a single item in a rule matches independently
- Consul: intentions not set between source and destination service

---

### Phase 6: Is routing configured correctly?

```bash
# Kuma — inspect what Envoy actually has
kumactl inspect dataplane <name> --type=clusters     # upstream clusters
kumactl inspect dataplane <name> --type=config-dump  # full xDS config
# Specific Envoy endpoints:
kubectl exec <pod> -c kuma-sidecar -- wget -qO- localhost:9901/clusters
kubectl exec <pod> -c kuma-sidecar -- wget -qO- 'localhost:9901/config_dump?resource=dynamic_active_listeners'

# Istio — decomposed config views
istioctl proxy-config cluster <pod>.<ns>       # clusters
istioctl proxy-config listener <pod>.<ns>      # listeners
istioctl proxy-config route <pod>.<ns>         # HTTP routes
istioctl proxy-config endpoint <pod>.<ns>      # backend pod IPs per cluster
# Human-readable summary with warnings:
istioctl x describe pod <pod>.<ns>

# Check for warming resources (blocks all traffic through that listener/cluster):
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=warming'
# listener_manager.total_listeners_warming > 0 = traffic blocked
```

**Common routing mistakes:**
- TLS mode mismatch: proxy sends mTLS, upstream expects plaintext (or vice versa)
- Istio: DestinationRule created without explicit `trafficPolicy.tls.mode` defaults to DISABLE,
  conflicts with mesh-wide ISTIO_MUTUAL → 503
- Port not named correctly (Istio requires `http-*`, `grpc-*` for L7 features)
- Missing EDS data: cluster exists but has 0 endpoints → `UH` (no healthy upstream)

---

### Phase 7: Examine live traffic

Only reach this phase when all above checks pass — meaning the issue is intermittent or
load-dependent.

```bash
# Enable Envoy debug logging (any mesh — admin API)
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- --post-data='' 'localhost:9901/logging?connection=trace&router=debug&upstream=debug'
# Reset after reproducing:
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- --post-data='' 'localhost:9901/logging?level=warning'

# Istio — traffic tap
istioctl x envoy-stats <pod>.<ns>   # per-endpoint error counts
istioctl experimental describe pod <pod>.<ns>

# Linkerd — live traffic tap
linkerd viz tap deploy/<name> -n <ns>
linkerd viz stat deploy/<name> -n <ns>  # success rate, RPS, latency

# Check Envoy access log response flags (in pod logs or access log sink):
# UF = upstream connection failure  UH = no healthy hosts
# NR = no route                     UO = circuit breaker open
# UAEX = denied by ext-authz        URX = retries exhausted
# UC = upstream connection terminated (keepalive race)
```

---

## Cross-Mesh CLI Quick Reference

| Check | Kuma | Istio | Linkerd | Consul |
|-------|------|-------|---------|--------|
| Overall health | `kumactl get zones` | `istioctl analyze` | `linkerd check` | `consul-k8s status` |
| Proxy enrolled? | `kumactl get dataplanes` | `istioctl proxy-status` | `linkerd check --proxy` | `consul-k8s proxy list` |
| Proxy config | `kumactl inspect dp <n> --type=config-dump` | `istioctl proxy-config all` | `linkerd diagnostics endpoints` | `consul-k8s proxy read` |
| Cert check | `scripts/mtls_check.py` | `istioctl proxy-config secret` | `linkerd check` (identity) | `consul debug` |
| Policy check | `kumactl get meshtrafficpermissions` | `istioctl x authz check` | `kubectl get serverauthorization` | `consul-k8s troubleshoot upstreams` |
| Why no injection? | check `kuma.io/sidecar-injection` label | `istioctl check-inject` | check `linkerd.io/inject` annotation | check `consul.hashicorp.com/connect-inject` |
| Live traffic | Envoy admin `/logging` | `istioctl x tap` | `linkerd viz tap` | access logs |
| Envoy admin port | `9901` | `15000` | `4191` (linkerd-proxy) | `19000` |

---

## Flaky E2E Test Patterns (Universal Across Meshes)

These appear in GitHub issues across linkerd/linkerd2, istio/istio, hashicorp/consul, kumahq/kuma:

| Pattern | Root cause | Fix |
|---------|-----------|-----|
| Proxy init race | App starts before proxy intercepts traffic | `holdApplicationUntilProxyStarts`, init container ordering |
| Cert provisioning delay | Test asserts mTLS before leaf cert issued | Wait for active secrets / cert present before traffic test |
| CNI init race | Network rules not in place on pod start | Explicit CNI readiness check before test |
| Config propagation delay | Policy applied, effect assumed immediate | Poll until policy is observed to take effect |
| Stale endpoint cache | Old pod IP still in routing table after restart | Wait for endpoint slice reconciliation |
| CP under load | istiod/kuma-cp overwhelmed by endpoint churn | Test isolation, reduce concurrent CP load |
| Clock skew | Cert validation fails when node clocks drift | NTP sync, check cert validity window |
