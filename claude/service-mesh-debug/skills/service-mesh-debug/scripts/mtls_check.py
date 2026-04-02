#!/usr/bin/env python3
"""
mTLS / SDS health check for any Envoy-based service mesh proxy.

Checks:
  1. SDS warming secrets (certs not yet delivered)
  2. Active secrets count (should be > 0 for mTLS mesh)
  3. TLS stats (handshakes, failures, SAN mismatches)
  4. Cert expiry (days until expiration)

Usage:
    # Kuma (default admin port 9901, container kuma-sidecar)
    python mtls_check.py <pod> [--namespace NS] [--expiry-warn-days N]

    # Istio (admin port 15000, container istio-proxy)
    python mtls_check.py <pod> -n <ns> --admin-port 15000 --container istio-proxy

    # Consul Connect (admin port 19000)
    python mtls_check.py <pod> -n <ns> --admin-port 19000 --container envoy-sidecar

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


def fetch_json(pod: str, ns: str, container: str, url: str) -> dict | list | None:
    rc, stdout = kubectl_exec(pod, ns, container, "wget", "-qO-", url)
    if rc != 0:
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return None


def fetch_stats(
    pod: str, ns: str, container: str, admin_port: int, filter_str: str
) -> dict[str, float]:
    rc, stdout = kubectl_exec(pod, ns, container, "wget", "-qO-",
                              f"localhost:{admin_port}/stats?usedonly&filter={filter_str}")
    if rc != 0:
        return {}
    stats: dict[str, float] = {}
    for line in stdout.splitlines():
        if ": " in line:
            key, _, val = line.partition(": ")
            with contextlib.suppress(ValueError):
                stats[key.strip()] = float(val.strip())
    return stats


def check_warming_secrets(pod: str, ns: str, container: str, admin_port: int) -> bool:
    data = fetch_json(pod, ns, container,
                      f"localhost:{admin_port}/config_dump?resource=dynamic_warming_secrets")
    if data is None:
        warn("Could not query warming secrets — is port 9901 accessible?")
        return False

    warming: list[str] = []
    try:
        for config in data.get("configs", []):
            for secret in config.get("dynamic_warming_secrets", []):
                name = secret.get("name", "<unnamed>")
                warming.append(name)
    except (AttributeError, KeyError):
        pass

    if not warming:
        ok("No warming secrets — all certs delivered by SDS")
        return True

    fail(f"{len(warming)} secret(s) still warming (cert not yet delivered):")
    for name in warming:
        print(f"    • {name}")
    print("    Tip: mTLS connections will fail with 'Secret is not supplied by SDS' until these deliver")
    print("    Tip: check control plane logs for SDS errors; restart sidecar if stuck > 60s")
    return False


def check_active_secrets(pod: str, ns: str, container: str, admin_port: int) -> bool:
    data = fetch_json(pod, ns, container,
                      f"localhost:{admin_port}/config_dump?resource=dynamic_active_secrets")
    if data is None:
        warn("Could not query active secrets")
        return False

    active: list[str] = []
    try:
        for config in data.get("configs", []):
            for secret in config.get("dynamic_active_secrets", []):
                name = secret.get("name", "<unnamed>")
                active.append(name)
    except (AttributeError, KeyError):
        pass

    if active:
        ok(f"{len(active)} active secret(s): {', '.join(active)}")
        return True

    fail("No active secrets — SDS has not delivered any certificates")
    print("    Tip: verify control plane is reachable and the dataplane is registered")
    return False


def check_tls_stats(pod: str, ns: str, container: str, admin_port: int) -> bool:
    stats = fetch_stats(pod, ns, container, admin_port, "ssl")
    passed = True

    handshakes = int(stats.get("listener.0.0.0.0_15001.ssl.handshake", 0)
                     or stats.get("listener.0.0.0.0_15006.ssl.handshake", 0)
                     or next((v for k, v in stats.items() if "ssl.handshake" in k and "fail" not in k), 0))
    errors = int(next((v for k, v in stats.items() if "ssl.connection_error" in k), 0))
    fail_verify = int(next((v for k, v in stats.items() if "ssl.fail_verify_error" in k), 0))
    fail_san = int(next((v for k, v in stats.items() if "ssl.fail_verify_san" in k), 0))

    if handshakes > 0:
        ok(f"TLS handshakes succeeded: {handshakes}")
    else:
        warn("No successful TLS handshakes recorded yet")

    if errors > 0:
        fail(f"ssl.connection_error = {errors}  (TLS handshake failures)")
        print(f"    Tip: enable trace logging → wget --post-data='' 'localhost:{admin_port}/logging?connection=trace'")
        passed = False
    else:
        ok("No TLS connection errors")

    if fail_verify > 0:
        fail(f"ssl.fail_verify_error = {fail_verify}  (CA verification failures — cert not trusted)")
        passed = False

    if fail_san > 0:
        fail(f"ssl.fail_verify_san = {fail_san}  (SAN mismatch — wrong identity in cert)")
        passed = False

    if fail_verify == 0 and fail_san == 0:
        ok("No cert verification failures")

    return passed


def check_cert_expiry(pod: str, ns: str, container: str, admin_port: int, warn_days: int) -> bool:
    data = fetch_json(pod, ns, container, f"localhost:{admin_port}/certs")
    if data is None:
        warn("Could not query /certs")
        return True  # non-fatal

    passed = True
    certs_checked = 0
    try:
        for cert_entry in data.get("certificates", []):
            for chain_cert in cert_entry.get("cert_chain", []):
                days = chain_cert.get("days_until_expiration")
                subject = chain_cert.get("subject", "<unknown>")
                if days is not None:
                    certs_checked += 1
                    if days <= 0:
                        fail(f"EXPIRED cert: {subject}")
                        passed = False
                    elif days <= warn_days:
                        warn(f"Cert expiring in {days}d: {subject}")
                    else:
                        ok(f"Cert valid for {days}d: {subject}")
    except (AttributeError, KeyError):
        pass

    if certs_checked == 0:
        warn("No certificate chain data found in /certs response")

    return passed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="mTLS / SDS health check for any Envoy-based service mesh proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Admin port defaults: Kuma=9901  Istio=15000  Consul=19000",
    )
    parser.add_argument("pod", help="Pod name")
    parser.add_argument("--namespace", "-n", default="default")
    parser.add_argument("--container", "-c", default="kuma-sidecar",
                        help="Sidecar container name (default: kuma-sidecar; Istio: istio-proxy)")
    parser.add_argument("--admin-port", "-p", type=int, default=9901,
                        help="Envoy admin port (default: 9901; Istio: 15000; Consul: 19000)")
    parser.add_argument("--expiry-warn-days", type=int, default=7,
                        help="Warn if cert expires within N days (default: 7)")
    args = parser.parse_args()

    print(f"{BOLD}mTLS check: {args.pod} ({args.namespace}/{args.container}) "
          f"admin:{args.admin_port}{RESET}\n")

    results: list[bool] = []

    print(f"{BOLD}[1] SDS warming secrets{RESET}")
    results.append(check_warming_secrets(args.pod, args.namespace, args.container, args.admin_port))

    print(f"\n{BOLD}[2] Active secrets{RESET}")
    results.append(check_active_secrets(args.pod, args.namespace, args.container, args.admin_port))

    print(f"\n{BOLD}[3] TLS stats{RESET}")
    results.append(check_tls_stats(args.pod, args.namespace, args.container, args.admin_port))

    print(f"\n{BOLD}[4] Cert expiry (warn threshold: {args.expiry_warn_days}d){RESET}")
    results.append(check_cert_expiry(
        args.pod, args.namespace, args.container, args.admin_port, args.expiry_warn_days))

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
