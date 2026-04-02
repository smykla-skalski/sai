# Fix Patterns

# Contents

1. [Pattern 1: Increase Eventually timeout](#pattern-1-increase-eventually-timeout)
2. [Pattern 2: Add xDS readiness gate](#pattern-2-add-xds-readiness-gate-before-traffic-assertion)
3. [Pattern 3: Fix bare Expect inside Eventually](#pattern-3-fix-bare-expect-inside-eventually)
4. [Pattern 4: Two-step pod wait](#pattern-4-two-step-pod-wait)
5. [Pattern 5: PodNameOfApp after kill](#pattern-5-podnameofapp-after-kill)
6. [Pattern 6: Confirm stable state with MustPassRepeatedly](#pattern-6-confirm-stable-state-with-mustpassrepeatedly)
7. [Pattern 7: Add AfterEachFailure debug hook](#pattern-7-add-aftereachfailure-debug-hook)
8. [Pattern 8: Wrap xDS config comparison in Eventually](#pattern-8-wrap-xds-config-comparison-in-eventually)
9. [Pattern 9: WaitForMesh for multi-zone sync](#pattern-9-waitformesh-for-multi-zone-sync)
10. [Pattern 10: Widen statistical tolerance](#pattern-10-widen-statistical-tolerance)

---

Copy-paste templates matched to each root cause. Always apply the minimal change.

---

## Pattern 1: Increase Eventually timeout

```go
// Gateway / policy propagation (was "30s")
}, "60s", "1s").Should(Succeed())

// mTLS / SVID / cross-zone (was "30s" or "60s")
}, "2m", "1s").Should(Succeed())
```

---

## Pattern 2: Add xDS readiness gate before traffic assertion

Insert this block between resource creation and traffic assertion:

```go
// Wait for xDS config to propagate to the dataplane
var podName string
Eventually(func(g Gomega) {
    pod, err := PodNameOfApp(cluster, appName, namespace)
    g.Expect(err).ToNot(HaveOccurred())
    podName = pod
}, "30s", "1s").Should(Succeed())

Eventually(func(g Gomega) {
    stdout, err := cluster.GetKumactlOptions().RunKumactlAndGetOutput(
        "inspect", "dataplane", podName+"."+namespace,
        "--mesh", meshName, "--type=clusters")
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(stdout).To(ContainSubstring("expected-cluster-name"))
}, "30s", "1s").Should(Succeed())
```

---

## Pattern 3: Fix bare Expect inside Eventually

```go
// BEFORE (broken — panics on first failure, no retry)
Eventually(func() {
    resp, err := client.CollectEchoResponse(...)
    Expect(err).ToNot(HaveOccurred())
    Expect(resp.Instance).To(Equal("server"))
}, "30s", "1s").Should(Succeed())

// AFTER (correct — retries through Eventually)
Eventually(func(g Gomega) {
    resp, err := client.CollectEchoResponse(...)
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(resp.Instance).To(Equal("server"))
}, "30s", "1s").Should(Succeed())
```

Search for all occurrences in the file: `Eventually(func() {` (no `g Gomega` parameter).

---

## Pattern 4: Two-step pod wait

```go
// BEFORE (only waits for pod object to exist)
Expect(cluster.Install(app.Install(...))).To(Succeed())
Expect(WaitApp("backend", namespace, 1, cluster)).To(Succeed())

// AFTER (also waits for readiness)
Expect(cluster.Install(app.Install(...))).To(Succeed())

// Two-step wait
Expect(k8s.WaitUntilNumPodsCreatedE(
    cluster.GetTesting(),
    cluster.GetKubectlOptions(namespace),
    metav1.ListOptions{LabelSelector: "app=backend"},
    1, DefaultRetries, DefaultTimeout,
)).To(Succeed())

pods := k8s.ListPods(cluster.GetTesting(),
    cluster.GetKubectlOptions(namespace),
    metav1.ListOptions{LabelSelector: "app=backend"})
for _, pod := range pods {
    Expect(k8s.WaitUntilPodAvailableE(
        cluster.GetTesting(),
        cluster.GetKubectlOptions(namespace),
        pod.Name, DefaultRetries, DefaultTimeout,
    )).To(Succeed())
}
```

---

## Pattern 5: PodNameOfApp after kill

```go
// BEFORE (race — terminating pod still listed)
Expect(cluster.DeletePod(podName, namespace)).To(Succeed())
newPod, err := PodNameOfApp(cluster, "backend", namespace)
Expect(err).ToNot(HaveOccurred())

// AFTER (wait for exactly one pod)
Expect(cluster.DeletePod(podName, namespace)).To(Succeed())

var newPod string
Eventually(func(g Gomega) {
    pod, err := PodNameOfApp(cluster, "backend", namespace)
    g.Expect(err).ToNot(HaveOccurred())
    newPod = pod
}, "30s", "1s").Should(Succeed())
```

---

## Pattern 6: Confirm stable state with MustPassRepeatedly

For critical assertions where a single pass isn't enough confidence:

```go
Eventually(func(g Gomega) {
    resp, err := client.CollectEchoResponse(
        cluster, "demo-client", "http://backend/",
        client.FromKubernetesPod(namespace, "demo-client"),
    )
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(resp.Instance).To(Equal("backend"))
}, "2m", "1s", MustPassRepeatedly(5)).Should(Succeed())
```

---

## Pattern 7: Add AfterEachFailure debug hook

Add to the test's `Describe` block if missing:

```go
AfterEachFailure(func() {
    DebugKube(KubeCluster, meshName, namespace)
})
```

For multi-zone tests:
```go
AfterEachFailure(func() {
    DebugKube(multizone.KubeZone1, meshName, namespace)
    DebugUniversal(multizone.Global, meshName)
})
```

---

## Pattern 8: Wrap xDS config comparison in Eventually

```go
// BEFORE (point-in-time comparison — fails if update not yet applied)
stdout, err := cluster.GetKumactlOptions().RunKumactlAndGetOutput(
    "inspect", "dataplane", name, "--type=clusters")
Expect(err).ToNot(HaveOccurred())
Expect(stdout).To(ContainSubstring("my-cluster"))

// AFTER (retries until config converges)
Eventually(func(g Gomega) {
    stdout, err := cluster.GetKumactlOptions().RunKumactlAndGetOutput(
        "inspect", "dataplane", name, "--type=clusters")
    g.Expect(err).ToNot(HaveOccurred())
    g.Expect(stdout).To(ContainSubstring("my-cluster"))
}, "30s", "1s").Should(Succeed())
```

---

## Pattern 9: WaitForMesh for multi-zone sync

Before asserting cross-zone connectivity:

```go
Expect(WaitForMesh(meshName, multizone.Zones())).To(Succeed())
```

---

## Pattern 10: Widen statistical tolerance

```go
// BEFORE (too tight for small N)
Expect(successCount).To(BeNumerically("~", 50, 5))  // ±5 out of 100

// AFTER option A: widen tolerance
Expect(successCount).To(BeNumerically("~", 50, 15))  // ±15

// AFTER option B: increase sample size
responses, err := client.CollectResponses(cluster, app, url,
    client.FromKubernetesPod(namespace, app),
    client.WithNumberOfRequests(200),  // was 20
)
```
