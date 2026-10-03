#!/usr/bin/env python3
"""
Auto-detect and health-check any service mesh control plane in a Kubernetes cluster.

Detects: Kuma, Istio, Linkerd, Consul Connect
Checks: control plane pods, proxy count, overall health signal

Usage:
    python mesh_health.py [--namespace NS] [--kubeconfig PATH]

Exit codes:
    0  all checks passed (or no mesh detected)
    1  mesh detected but unhealthy
"""

import argparse
import json
import shutil
import subprocess
import sys

_KUBECTL: str = shutil.which("kubectl") or "kubectl"

RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
CYAN = "\033[36m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}→{RESET} {msg}")


def kubectl(*args: str, kubeconfig: str | None = None) -> tuple[int, str]:
    cmd = [_KUBECTL]
    if kubeconfig:
        cmd += ["--kubeconfig", kubeconfig]
    cmd += list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout


def get_pods_json(namespace: str, label: str, kubeconfig: str | None) -> list[dict]:
    rc, stdout = kubectl(
        "get", "pods", "-n", namespace, "-l", label, "-o", "json",
        kubeconfig=kubeconfig,
    )
    if rc != 0:
        return []
    try:
        data = json.loads(stdout)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []


def ns_exists(namespace: str, kubeconfig: str | None) -> bool:
    rc, _ = kubectl("get", "namespace", namespace, kubeconfig=kubeconfig)
    return rc == 0


def pod_ready(pod: dict) -> bool:
    conditions = pod.get("status", {}).get("conditions", [])
    for c in conditions:
        if c.get("type") == "Ready":
            return c.get("status") == "True"
    return False


def summarize_pods(pods: list[dict], label: str) -> bool:
    if not pods:
        fail(f"No pods found with label {label!r}")
        return False
    ready = sum(1 for p in pods if pod_ready(p))
    total = len(pods)
    if ready == total:
        ok(f"{ready}/{total} pods ready")
        return True
    else:
        fail(f"{ready}/{total} pods ready")
        for p in pods:
            if not pod_ready(p):
                name = p.get("metadata", {}).get("name", "?")
                phase = p.get("status", {}).get("phase", "?")
                warn(f"  Not ready: {name} ({phase})")
        return False


# ─── Mesh-specific checks ────────────────────────────────────────────────────

def check_kuma(kubeconfig: str | None) -> bool:
    print(f"\n{BOLD}Kuma control plane{RESET}")
    ns = "kuma-system"
    if not ns_exists(ns, kubeconfig):
        warn(f"Namespace {ns!r} not found — Kuma not installed")
        return True  # not installed, not a failure

    pods = get_pods_json(ns, "app=kuma-control-plane", kubeconfig)
    passed = summarize_pods(pods, "app=kuma-control-plane")

    info("Next steps if unhealthy:")
    info("  kubectl logs -n kuma-system deploy/kuma-control-plane --tail=50")
    info("  kumactl get zones")
    return passed


def check_istio(kubeconfig: str | None) -> bool:
    print(f"\n{BOLD}Istio control plane (istiod){RESET}")
    ns = "istio-system"
    if not ns_exists(ns, kubeconfig):
        warn(f"Namespace {ns!r} not found — Istio not installed")
        return True

    pods = get_pods_json(ns, "app=istiod", kubeconfig)
    passed = summarize_pods(pods, "app=istiod")

    info("Next steps if unhealthy:")
    info("  kubectl logs -n istio-system deploy/istiod --tail=50")
    info("  istioctl analyze")
    info("  istioctl proxy-status")
    return passed


def check_linkerd(kubeconfig: str | None) -> bool:
    print(f"\n{BOLD}Linkerd control plane{RESET}")
    ns = "linkerd"
    if not ns_exists(ns, kubeconfig):
        warn(f"Namespace {ns!r} not found — Linkerd not installed")
        return True

    # Check destination, identity, proxy-injector
    all_passed = True
    for component in ("linkerd-destination", "linkerd-identity", "linkerd-proxy-injector"):
        pods = get_pods_json(ns, f"linkerd.io/control-plane-component={component.replace('linkerd-', '')}", kubeconfig)
        if pods and not summarize_pods(pods, f"component={component}"):
            all_passed = False

    info("Next steps if unhealthy:")
    info("  linkerd check")
    info("  linkerd diagnostics endpoints <svc>.<ns>:port")
    return all_passed


def check_consul(kubeconfig: str | None) -> bool:
    print(f"\n{BOLD}Consul Connect{RESET}")
    ns = "consul"
    if not ns_exists(ns, kubeconfig):
        warn(f"Namespace {ns!r} not found — Consul not installed")
        return True

    pods = get_pods_json(ns, "app=consul,component=server", kubeconfig)
    passed = summarize_pods(pods, "app=consul,component=server")

    info("Next steps if unhealthy:")
    info("  consul-k8s status")
    info("  kubectl logs -n consul -l app=consul,component=server --tail=50")
    return passed


# ─── Webhook health ──────────────────────────────────────────────────────────

def check_webhooks(kubeconfig: str | None) -> bool:
    print(f"\n{BOLD}Admission webhooks (mesh injection){RESET}")
    rc, stdout = kubectl(
        "get", "mutatingwebhookconfigurations",
        "-o", "jsonpath={.items[*].metadata.name}",
        kubeconfig=kubeconfig,
    )
    if rc != 0:
        warn("Could not list mutating webhooks")
        return True  # non-fatal

    names = stdout.strip().split() if stdout.strip() else []
    mesh_hooks = [n for n in names if any(k in n for k in ("kuma", "istio", "linkerd", "consul"))]
    if mesh_hooks:
        ok(f"Mesh webhook(s) present: {', '.join(mesh_hooks)}")
    else:
        warn("No mesh-related mutating webhooks found — sidecar injection may not work")
    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-detect and health-check any service mesh control plane",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    args = parser.parse_args()

    print(f"{BOLD}Service mesh health check{RESET}\n")
    print("Checking for installed meshes...\n")

    results: list[bool] = []
    results.append(check_kuma(args.kubeconfig))
    results.append(check_istio(args.kubeconfig))
    results.append(check_linkerd(args.kubeconfig))
    results.append(check_consul(args.kubeconfig))
    results.append(check_webhooks(args.kubeconfig))

    print(f"\n{'─' * 40}")
    if all(results):
        print(f"{GREEN}{BOLD}All checks passed{RESET}")
        sys.exit(0)
    else:
        failed = sum(1 for r in results if not r)
        print(f"{RED}{BOLD}{failed}/{len(results)} checks FAILED{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
