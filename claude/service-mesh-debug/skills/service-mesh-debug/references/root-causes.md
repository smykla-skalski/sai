# Root Cause Taxonomy

# Contents

1. [Short `Eventually` timeout](#1-short-eventually-timeout)
2. [Missing xDS readiness gate](#2-missing-xds-readiness-gate)
3. [Bare `Expect` inside `Eventually`](#3-bare-expect-inside-eventually)
4. [Pod not available after create](#4-pod-not-available-after-create)
5. [`PodNameOfApp` race after kill](#5-podnameofapp-race-after-kill)
6. [External component not awaited](#6-external-component-not-awaited)
7. [xDS config diff before convergence](#7-xds-config-diff-before-convergence)
8. [SDS secret delivery timing](#8-sds-secret-delivery-timing)
9. [Statistical assertions with tight margins](#9-statistical-assertions-with-tight-margins)
10. [Circuit breaker tripped](#10-circuit-breaker-tripped)
11. [Outlier detection ejection](#11-outlier-detection-ejection)

---

Sourced from Kuma PR history (PRs: #15684, #15916, #15920, #15915, #12744, #11489, #12820, #11827, #8558, #8547, #14957, #3913).

---

## 1. Short `Eventually` timeout

**Signal:** `"30s"` or `"15s"` timeout on assertions involving gateway, policy propagation, or mTLS.

**Why it fails in CI:** CI runners are loaded. The CP reconciliation pipeline stacks up:
policy write → KDS sync → xDS push → Envoy reload → health check cycle. Can take 5–25s locally,
25s+ in CI. What passes locally fails in CI under load.

**Fix:** Increase timeout to match the operation:
- Gateway / ingress policy: `"60s"`
- mTLS / SVID / cross-zone: `"2m"`

---

## 2. Missing xDS readiness gate

**Signal:** Traffic assertion immediately follows `Install(...)` or `kubectl apply` with no
intermediate `Eventually` waiting for config propagation.

**Why it fails:** The CP has to reconcile the new resource, push xDS to all affected dataplanes,
and Envoy must reload its config. This isn't instant — it's a pipeline with multiple async steps.

**Fix:** Before asserting traffic, verify the expected cluster/route exists in Envoy's config:
```go
Eventually(func(g Gomega) {
    stdout, err := cluster.GetKumactlOptions().RunKumactlAndGetOutput(
        "inspect", "dataplane", podName+"."+namespace, "--type=clusters")
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(stdout).To(ContainSubstring("expected-cluster"))
}, "30s", "1s").Should(Succeed())
```

---

## 3. Bare `Expect` inside `Eventually`

**Signal:** `Eventually(func() { Expect(...) })` — the callback takes no argument.

**Why it fails:** When `Expect` inside the callback fails, it panics rather than returning an
error. `Eventually` catches panics but this bypasses the retry logic — the test fails immediately
on the first failed assertion instead of retrying until timeout.

**Fix:** Add `g Gomega` parameter and use `g.Expect`:
```go
// Wrong — panics on first failure
Eventually(func() {
    Expect(x).To(Equal(y))
}, "30s", "1s").Should(Succeed())

// Correct — retries on failure
Eventually(func(g Gomega) {
    g.Expect(x).To(Equal(y))
}, "30s", "1s").Should(Succeed())
```

This is the single most impactful mechanical fix. Affects many tests.

---

## 4. Pod not available after create

**Signal:** `WaitUntilNumPodsCreatedE` called without a subsequent `WaitUntilPodAvailableE`.

**Why it fails:** `WaitUntilNumPodsCreatedE` waits for the pod **object** to exist in the API
server. This happens before the container image is pulled, before init containers run, before
the readiness probe passes. Asserting against a pod in `Pending` or `Init` state causes flakes.

**Fix:** Two-step wait:
```go
// Step 1: wait for pod object
Expect(k8s.WaitUntilNumPodsCreatedE(t, opts, selector, 1, retries, timeout)).To(Succeed())
// Step 2: wait for pod to pass readiness checks
pods := k8s.ListPods(t, opts, selector)
for _, pod := range pods {
    Expect(k8s.WaitUntilPodAvailableE(t, opts, pod.Name, retries, timeout)).To(Succeed())
}
```

Also applies to external components: SPIRE server, cert-manager, Postgres, KIC.

---

## 5. `PodNameOfApp` race after kill

**Signal:** `PodNameOfApp` called immediately after `KillAppPod` or pod deletion.

**Why it fails:** The terminating pod briefly remains in the pod list (in `Terminating` state).
`PodNameOfApp` expects exactly 1 pod; finding 2 returns an error.

**Fix:** Wrap in `Eventually` until exactly one pod exists:
```go
var podName string
Eventually(func(g Gomega) {
    pod, err := PodNameOfApp(cluster, appName, namespace)
    g.Expect(err).ToNot(HaveOccurred())
    podName = pod
}, "30s", "1s").Should(Succeed())
```

---

## 6. External component not awaited

**Signal:** SPIRE / cert-manager / Postgres / KIC created with `Install(...)` but no per-pod
availability check before the test proceeds.

**Why it fails:** `Install` returns once the resource is applied, not once the component is
running. These components have longer startup times than typical application pods.

**Fix:** After install, explicitly wait for each pod:
```go
pods := k8s.ListPods(t, opts, metav1.ListOptions{LabelSelector: "app=spire-server"})
for _, pod := range pods {
    Expect(k8s.WaitUntilPodAvailableE(t, opts, pod.Name, DefaultRetries*3, DefaultTimeout)).To(Succeed())
}
```

For SPIRE specifically, also poll for SVID readiness:
```go
Eventually(func(g Gomega) {
    output, err := k8s.RunKubectlAndGetOutputE(...)
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(output).To(ContainSubstring("Successfully initialized"))
}, "2m", "1s").Should(Succeed())
```

---

## 7. xDS config diff before convergence

**Signal:** `config_dump` or `kumactl inspect --type=clusters` compared against expected value
outside an `Eventually` block.

**Why it fails:** xDS updates are asynchronous. At the moment of comparison, the new config may
not have been delivered to Envoy yet.

**Fix:** Wrap the comparison in `Eventually`:
```go
Eventually(func(g Gomega) {
    dump, err := cluster.GetKumactlOptions().RunKumactlAndGetOutput(
        "inspect", "dataplane", name, "--type=config-dump")
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(dump).To(ContainSubstring("expected-value"))
}, "30s", "1s").Should(Succeed())
```

---

## 8. SDS secret delivery timing

**Signal:** mTLS test fails with `Secret is not supplied by SDS` in Envoy transport failure reason,
or TLS handshake fails right after a new pod starts.

**Why it fails:** When a new Envoy sidecar starts, it connects to SDS (Kuma CP) to get its leaf
certificate. Until the cert is delivered, Envoy queues connections but can't complete TLS.
The cert generation and delivery takes 2–15s.

**Fix:** Before asserting mTLS connectivity, wait for warming secrets to drain:
```go
Eventually(func(g Gomega) {
    output, err := k8s.RunKubectlExecE(t, opts, podName, "kuma-sidecar",
        "wget", "-qO-", "localhost:9901/config_dump?resource=dynamic_warming_secrets")
    g.Expect(err).ToNot(HaveOccurred())
    var dump map[string]interface{}
    g.Expect(json.Unmarshal([]byte(output), &dump)).To(Succeed())
    // warming_secrets should be absent or empty
    g.Expect(output).To(Or(ContainSubstring(`"configs": []`), Not(ContainSubstring("warming_secrets"))))
}, "30s", "1s").Should(Succeed())
```

Or more pragmatically, increase the mTLS connectivity timeout to `"2m"`.

---

## 9. Statistical assertions with tight margins

**Signal:** Traffic split test asserting exact percentages (e.g., `50% ± 5%`) with small sample
sizes (N < 100).

**Why it fails:** Statistical variance. With N=10 and a 50/50 split, seeing 7/3 is not unusual.

**Fix:** Increase sample size (N ≥ 100 for percentage assertions) or widen the tolerance:
```go
// Instead of asserting 50% ± 5%
Expect(successRate).To(BeNumerically("~", 0.5, 0.15))  // ± 15% tolerance
// And increase N
client.WithNumberOfRequests(100)
```

---

## 10. Circuit breaker tripped

**Signal:** Test failures with `UO` response flag (upstream overflow). More common when tests run
concurrently or when retry policies are active.

**Why it fails:** Envoy's default circuit breaker limits are: 1024 max connections, 1024 max
pending requests, 1024 max requests, **3 max retries**. The retry pool is small and exhausts
quickly under concurrent test load.

**Diagnosis:**
```bash
kubectl exec <pod> -c kuma-sidecar -- wget -qO- \
  'localhost:9901/stats?filter=circuit_breakers'
# Look for: cx_open = 1, rq_retry_open = 1
```

**Fix:** Either disable retries in the test's traffic policy, or increase CB limits via
MeshCircuitBreaker policy for the test mesh.

---

## 11. Outlier detection ejection

**Signal:** Test injects failures (5xx, timeouts) to test fault tolerance, then later asserts
normal traffic — but normal traffic fails because the target host was ejected.

**Why it fails:** Outlier detection ejects a host after a configurable threshold of failures.
Default base ejection time: 30s. The host won't receive traffic during this window.

**Diagnosis:**
```bash
kubectl exec <pod> -c kuma-sidecar -- wget -qO- \
  'localhost:9901/stats?filter=outlier_detection'
# ejections_active > 0 = host currently ejected
```

**Fix:** After the fault-injection phase, wait for ejections to clear before asserting recovery:
```go
Eventually(func(g Gomega) {
    stats, err := getEnvoyStats(pod, "outlier_detection.ejections_active")
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(stats).To(Equal("0"))
}, "60s", "1s").Should(Succeed())
```
Or disable outlier detection in the test mesh via MeshCircuitBreaker policy.
