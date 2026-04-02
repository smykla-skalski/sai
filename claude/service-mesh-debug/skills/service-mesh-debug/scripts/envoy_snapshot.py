#!/usr/bin/env python3
"""
Collect a full Envoy diagnostic snapshot from any Envoy-based sidecar.

Usage:
    # Kuma (default admin port 9901, container kuma-sidecar)
    python envoy_snapshot.py <pod> [--namespace NS] [--output-dir DIR]

    # Istio (admin port 15000, container istio-proxy)
    python envoy_snapshot.py <pod> -n <ns> --admin-port 15000 --container istio-proxy

    # Consul Connect (admin port 19000)
    python envoy_snapshot.py <pod> -n <ns> --admin-port 19000 --container envoy-sidecar

Output directory (default: ./envoy-snapshot-<pod>-<timestamp>/) contains:
    config_dump.json, stats.txt, clusters.txt, listeners.json,
    certs.json, server_info.json, init_dump.json
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_KUBECTL: str = shutil.which("kubectl") or "kubectl"
_K8S_NAME_RE: re.Pattern[str] = re.compile(r"^[a-z0-9][a-z0-9._-]{0,251}$")


def _validate_k8s_name(value: str, label: str) -> None:
    """Validate a Kubernetes resource name to prevent injection."""
    if not _K8S_NAME_RE.match(value):
        sys.exit(f"Invalid {label} {value!r}: must match [a-z0-9][a-z0-9._-]{{0,251}}")


_ENDPOINT_PATHS = [
    ("config_dump.json",  "/config_dump?include_eds"),
    ("stats.txt",         "/stats?usedonly"),
    ("clusters.txt",      "/clusters"),
    ("listeners.json",    "/listeners?format=json"),
    ("certs.json",        "/certs"),
    ("server_info.json",  "/server_info"),
    ("init_dump.json",    "/init_dump"),
]


def kubectl_exec(pod: str, namespace: str, container: str, *cmd: str) -> tuple[int, str, str]:
    _validate_k8s_name(pod, "pod")
    _validate_k8s_name(namespace, "namespace")
    _validate_k8s_name(container, "container")
    full_cmd = [_KUBECTL, "exec", pod, "-n", namespace, "-c", container, "--", *cmd]
    result = subprocess.run(full_cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout, result.stderr


def fetch_endpoint(pod: str, namespace: str, container: str, url: str) -> str | None:
    rc, stdout, stderr = kubectl_exec(pod, namespace, container, "wget", "-qO-", url)
    if rc != 0:
        print(f"  WARN: {url} failed: {stderr.strip()}", file=sys.stderr)
        return None
    return stdout


def pretty_json(text: str) -> str:
    try:
        return json.dumps(json.loads(text), indent=2)
    except (json.JSONDecodeError, ValueError):
        return text


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect Envoy diagnostic snapshot from any Envoy-based sidecar",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Admin port defaults: Kuma=9901  Istio=15000  Consul=19000",
    )
    parser.add_argument("pod", help="Pod name")
    parser.add_argument("--namespace", "-n", default="default", help="Kubernetes namespace (default: default)")
    parser.add_argument("--container", "-c", default="kuma-sidecar",
                        help="Sidecar container name (default: kuma-sidecar; Istio: istio-proxy)")
    parser.add_argument("--admin-port", "-p", type=int, default=9901,
                        help="Envoy admin port (default: 9901; Istio: 15000; Consul: 19000)")
    parser.add_argument("--output-dir", "-o", help="Output directory (default: ./envoy-snapshot-<pod>-<ts>/)")
    args = parser.parse_args()

    endpoints = [(f, f"localhost:{args.admin_port}{path}") for f, path in _ENDPOINT_PATHS]

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.output_dir) if args.output_dir else Path(f"envoy-snapshot-{args.pod}-{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Collecting snapshot from {args.pod}/{args.container} in namespace {args.namespace} "
          f"(admin port {args.admin_port})")
    print(f"Output: {out_dir}/\n")

    for filename, url in endpoints:
        print(f"  Fetching {url} ...", end=" ", flush=True)
        content = fetch_endpoint(args.pod, args.namespace, args.container, url)
        if content is not None:
            if filename.endswith(".json"):
                content = pretty_json(content)
            (out_dir / filename).write_text(content)
            print(f"OK ({len(content)} bytes)")
        else:
            print("FAILED")

    # Write a manifest
    manifest = {
        "pod": args.pod,
        "namespace": args.namespace,
        "container": args.container,
        "admin_port": args.admin_port,
        "timestamp": ts,
        "files": [f for f, _ in endpoints],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"\nSnapshot saved to: {out_dir}/")
    print("Tip: compare two snapshots with: diff -r snapshot-before/ snapshot-after/")


if __name__ == "__main__":
    main()
