# Envoy Admin API Debug Reference

# Contents

1. [Access](#access)
2. [Diagnostic workflow for e2e failures](#diagnostic-workflow-for-e2e-failures)
3. [Response flag quick reference](#response-flag-quick-reference)
4. [Kuma inspect commands](#kuma-inspect-commands)
5. [Full config dump (filtered)](#full-config-dump-filtered)
6. [Collect diagnostic data for issue filing](#collect-diagnostic-data-for-issue-filing)

---

Kuma sidecar exposes Envoy admin on port 9901.

## Access

```bash
# From pod (kuma-sidecar container)
kubectl exec <pod> -c kuma-sidecar -- wget -qO- localhost:9901/<endpoint>

# Port-forward alternative
kubectl port-forward <pod> 9901:9901
```

---

## Diagnostic workflow for e2e failures

### Step 1: Is Envoy connected to CP?

```bash
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=control_plane'
# control_plane.connected_state = 1 (good), 0 (disconnected)
# control_plane.pending_requests > 0 (backpressure)
```

### Step 2: Any config rejections (NACKs)?

```bash
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?usedonly&filter=update_rejected'
# cluster_manager.cds.update_rejected > 0 → bad cluster config
# listener_manager.lds.update_rejected > 0 → bad listener config
```

### Step 3: Any resources stuck warming?

Resources in "warming" state don't serve traffic yet.

```bash
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=warming'
# listener_manager.total_listeners_warming > 0 = stuck

# See which ones:
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/config_dump?resource=dynamic_warming_listeners' | jq .
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/config_dump?resource=dynamic_warming_secrets' | jq .
```

**Warming rules:**
- Clusters warm after CDS + EDS both arrive
- Listeners warm after LDS + RDS both arrive
- If either is missing → hangs indefinitely

### Step 4: Check cluster health

```bash
kubectl exec <pod> -c kuma-sidecar -- wget -qO- localhost:9901/clusters | \
  grep -E 'health_flags|membership_healthy|cx_active'
```

### Step 5: TLS cert status

```bash
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- localhost:9901/certs | jq '.certificates[].cert_chain[].days_until_expiration'

kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=ssl'
# ssl.fail_verify_error → CA trust issue
# ssl.fail_verify_san → SAN mismatch
# ssl.handshake → successful handshakes (should be > 0 if mTLS working)
```

### Step 6: Circuit breaker / outlier

```bash
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=circuit_breakers'
# cx_open = 1 → connection CB open
# rq_retry_open = 1 → retry CB open

kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/stats?filter=outlier_detection'
# ejections_active > 0 → host currently ejected
```

### Step 7: Enable verbose logging (temporarily)

```bash
# Enable
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- --post-data='' 'localhost:9901/logging?connection=trace&upstream=debug&router=debug'

# Reset after reproducing
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- --post-data='' 'localhost:9901/logging?level=warning'
```

---

## Response flag quick reference

Appears in Envoy access logs as `%RESPONSE_FLAGS%`.

| Flag | Meaning | Common cause in e2e |
|------|---------|---------------------|
| `UF` | Upstream connection failure | Pod not running, port closed, wrong port |
| `UH` | No healthy upstream hosts | Health check failing, all hosts ejected |
| `UC` | Upstream connection terminated | HTTP/1.1 keepalive race |
| `UO` | Upstream overflow | Circuit breaker open |
| `UT` | Upstream request timeout | Timeout too short |
| `NR` | No route | xDS not delivered yet, name mismatch |
| `URX` | Retries exhausted | All retries used (check retry stats) |
| `UAEX` | Denied by ext-authz | AuthorizationPolicy blocking |
| `DC` | Downstream conn terminated | Client disconnected (test teardown race) |

---

## Kuma inspect commands

```bash
# Which policies match this dataplane?
kumactl inspect dataplane <name> --mesh=default

# What clusters does this DP know about?
kumactl inspect dataplane <name> --type=clusters

# Full xDS config delivered to this DP
kumactl inspect dataplane <name> --type=config-dump

# Is the dataplane connected? (offline = no xDS stream)
kumactl get dataplanes --mesh=default -o json | \
  jq '.items[] | {name, connected: .status.connected}'
```

---

## Full config dump (filtered)

```bash
# Listeners
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- localhost:9901/config_dump | \
  jq '.configs[] | select(."@type" | contains("Listeners"))'

# Clusters
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- localhost:9901/config_dump | \
  jq '.configs[] | select(."@type" | contains("Clusters"))'

# Routes
kubectl exec <pod> -c kuma-sidecar -- \
  wget -qO- 'localhost:9901/config_dump?resource=dynamic_route_configs'
```

---

## Collect diagnostic data for issue filing

```bash
POD=<your-pod>
NS=<namespace>

kubectl exec $POD -n $NS -c kuma-sidecar -- wget -qO- localhost:9901/config_dump   > config_dump.json
kubectl exec $POD -n $NS -c kuma-sidecar -- wget -qO- localhost:9901/stats          > stats.txt
kubectl exec $POD -n $NS -c kuma-sidecar -- wget -qO- localhost:9901/clusters       > clusters.txt
kubectl exec $POD -n $NS -c kuma-sidecar -- wget -qO- localhost:9901/listeners      > listeners.txt
kubectl exec $POD -n $NS -c kuma-sidecar -- wget -qO- localhost:9901/certs          > certs.json
kubectl exec $POD -n $NS -c kuma-sidecar -- wget -qO- localhost:9901/server_info    > server_info.json
```
