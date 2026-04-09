#!/usr/bin/env python3
"""
Quick xDS health check for any Envoy-based service mesh proxy.

Checks in order:
  1. Control plane connection (connected_state)
  2. NACKs (update_rejected counters)
  3. Warming resources (listeners/clusters stuck in warming)
  4. Optionally verify a specific cluster or route name is present

Usage:
    # Kuma (default admin port 9901, container kuma-sidecar)
    python xds_check.py <pod> [--namespace NS] [--cluster NAME] [--route NAME]

    # Istio (admin port 15000, container istio-proxy)
    python xds_check.py <pod> -n <ns> --admin-port 15000 --container istio-proxy

    # Consul Connect (admin port 19000)
    python xds_check.py <pod> -n <ns> --admin-port 19000 --container envoy-sidecar

Exit codes:
    0  all checks passed
    1  one or more checks failed
"""

import argparse
import contextlib
import json
import re
import shutil
import subprocess
import sys


_KUBECTL: str = shutil.which("kubectl") or "kubectl"
_K8S_NAME_RE: re.Pattern[str] = re.compile(r"^[a-z0-9][a-z0-9._-]{0,251}$")


def _validate_k8s_name(value: str, label: str) -> None:
    """Validate a Kubernetes resource name to prevent injection."""
    if not _K8S_NAME_RE.match(value):
        sys.exit(f"Invalid {label} {value!r}: must match [a-z0-9][a-z0-9._-]{{0,251}}")


RESET = "\033[0m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}!{RESET} {msg}")


def kubectl_exec(pod: str, namespace: str, container: str, *cmd: str) -> tuple[int, str]:
    _validate_k8s_name(pod, "pod")
    _validate_k8s_name(namespace, "namespace")
    _validate_k8s_name(container, "container")
    result = subprocess.run(
        [_KUBECTL, "exec", pod, "-n", namespace, "-c", container, "--", *cmd],
        capture_output=True, text=True, check=False,
    )
    return result.returncode, result.stdout


def fetch_stats(
    pod: str, ns: str, container: str, admin_port: int, filter_str: str = ""
) -> dict[str, float]:
    url = f"localhost:{admin_port}/stats?usedonly"
    if filter_str:
        url += f"&filter={filter_str}"
    rc, stdout = kubectl_exec(pod, ns, container, "wget", "-qO-", url)
    if rc != 0:
        return {}
    stats: dict[str, float] = {}
    for line in stdout.splitlines():
        if ": " in line:
            key, _, val = line.partition(": ")
            with contextlib.suppress(ValueError):
                stats[key.strip()] = float(val.strip())
    return stats


def fetch_json(
    pod: str, ns: str, container: str, url: str
) -> dict | list | None:
    rc, stdout = kubectl_exec(pod, ns, container, "wget", "-qO-", url)
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def check_cp_connection(
    pod: str, ns: str, container: str, admin_port: int
) -> bool:
    stats = fetch_stats(pod, ns, container, admin_port, "control_plane")
    connected = stats.get("control_plane.connected_state", -1)
    pending = stats.get("control_plane.pending_requests", 0)

    if connected == 1:
        ok(f"Control plane connected (pending_requests={int(pending)})")
        return True
    elif connected == 0:
        fail("Control plane DISCONNECTED (connected_state=0)")
        return False
    else:
        warn(f"Could not read control_plane.connected_state — is port {admin_port} accessible?")
        return False


def check_nacks(pod: str, ns: str, container: str, admin_port: int) -> bool:
    stats = fetch_stats(pod, ns, container, admin_port, "update_rejected")
    rejected = {k: int(v) for k, v in stats.items() if v > 0}
    if not rejected:
        ok("No NACKs (all xDS updates accepted)")
        return True
    for k, v in rejected.items():
        fail(f"NACK: {k} = {v}  (config rejected by Envoy)")
    print(f"    Tip: enable config logging → kubectl exec ... -- wget -qO- --post-data='' "
          f"'localhost:{admin_port}/logging?config=debug'")
    return False


def check_warming(pod: str, ns: str, container: str, admin_port: int) -> bool:
    stats = fetch_stats(pod, ns, container, admin_port, "warming")
    warming_listeners = int(stats.get("listener_manager.total_listeners_warming", 0))
    warming_clusters = int(stats.get("cluster_manager.warming_clusters", 0))

    passed = True
    if warming_listeners > 0:
        fail(f"{warming_listeners} listener(s) stuck in warming")
        data = fetch_json(pod, ns, container,
                          f"localhost:{admin_port}/config_dump?resource=dynamic_warming_listeners")
        if data:
            names = _extract_warming_names(data, "dynamic_warming_listeners", "listener")
            if names:
                print(f"    Warming listeners: {', '.join(names)}")
        print("    Tip: warming listeners block traffic until RDS/SDS delivers all dependencies")
        passed = False
    else:
        ok("No warming listeners")

    if warming_clusters > 0:
        fail(f"{warming_clusters} cluster(s) stuck in warming")
        data = fetch_json(pod, ns, container,
                          f"localhost:{admin_port}/config_dump?resource=dynamic_warming_clusters")
        if data:
            names = _extract_warming_names(data, "dynamic_warming_clusters", "cluster")
            if names:
                print(f"    Warming clusters: {', '.join(names)}")
        print("    Tip: warming clusters need both CDS + EDS before they become active")
        passed = False
    else:
        ok("No warming clusters")

    return passed


def _extract_warming_names(data: dict | list, section: str, resource_key: str) -> list[str]:
    names: list[str] = []
    try:
        configs = data.get("configs", []) if isinstance(data, dict) else []
        for config in configs:
            for item in config.get(section, []):
                name = item.get(resource_key, {}).get("name", "")
                if name:
                    names.append(name)
    except (AttributeError, KeyError):
        pass
    return names


def check_cluster_present(
    pod: str, ns: str, container: str, admin_port: int, cluster_name: str
) -> bool:
    rc, stdout = kubectl_exec(
        pod, ns, container, "wget", "-qO-",
        f"localhost:{admin_port}/config_dump?resource=dynamic_active_clusters&name_regex={cluster_name}",
    )
    if rc != 0:
        fail(f"Cluster '{cluster_name}': could not query config_dump")
        return False
    if cluster_name in stdout:
        ok(f"Cluster '{cluster_name}' is active")
        return True
    fail(f"Cluster '{cluster_name}' NOT found in active clusters")
    print("    Tip: check if it's in warming → add ?resource=dynamic_warming_clusters")
    return False


def check_route_present(
    pod: str, ns: str, container: str, admin_port: int, route_name: str
) -> bool:
    rc, stdout = kubectl_exec(
        pod, ns, container, "wget", "-qO-",
        f"localhost:{admin_port}/config_dump?resource=dynamic_route_configs",
    )
    if rc != 0:
        fail(f"Route '{route_name}': could not query config_dump")
        return False
    if route_name in stdout:
        ok(f"Route '{route_name}' found in route configs")
        return True
    fail(f"Route '{route_name}' NOT found in route configs")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quick xDS health check for any Envoy-based service mesh proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Admin port defaults: Kuma=9901  Istio=15000  Consul=19000",
    )
    parser.add_argument("pod", help="Pod name")
    parser.add_argument("--namespace", "-n", default="default")
    parser.add_argument("--container", "-c", default="kuma-sidecar",
                        help="Sidecar container name (default: kuma-sidecar; Istio: istio-proxy)")
    parser.add_argument("--admin-port", "-p", type=int, default=9901,
                        help="Envoy admin port (default: 9901; Istio: 15000; Consul: 19000)")
    parser.add_argument("--cluster", help="Assert this cluster name exists in active clusters")
    parser.add_argument("--route", help="Assert this route name exists in route configs")
    args = parser.parse_args()

    print(f"{BOLD}xDS check: {args.pod} ({args.namespace}/{args.container}) "
          f"admin:{args.admin_port}{RESET}\n")

    results: list[bool] = []

    print(f"{BOLD}[1] Control plane connection{RESET}")
    results.append(check_cp_connection(args.pod, args.namespace, args.container, args.admin_port))

    print(f"\n{BOLD}[2] NACKs{RESET}")
    results.append(check_nacks(args.pod, args.namespace, args.container, args.admin_port))

    print(f"\n{BOLD}[3] Warming resources{RESET}")
    results.append(check_warming(args.pod, args.namespace, args.container, args.admin_port))

    if args.cluster:
        print(f"\n{BOLD}[4] Cluster presence{RESET}")
        results.append(check_cluster_present(
            args.pod, args.namespace, args.container, args.admin_port, args.cluster))

    if args.route:
        print(f"\n{BOLD}[5] Route presence{RESET}")
        results.append(check_route_present(
            args.pod, args.namespace, args.container, args.admin_port, args.route))

    passed = sum(results)
    total = len(results)
    print(f"\n{'─' * 40}")
    if all(results):
        print(f"{GREEN}{BOLD}All {total} checks passed{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}{total - passed}/{total} checks FAILED{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
