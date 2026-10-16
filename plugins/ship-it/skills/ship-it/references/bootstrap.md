# Bootstrap

Use `python3 <plugin>/skills/ship-it/scripts/plugin_pins.py`:

1. Probe `supported`. Unsupported (including Windows without flock/ps): disclose missing retention, forward installed root, skip acquire/release/collect and avoid provider updates. Other failures block.
2. Use the manifest root and long-lived host PID (host metadata, never a tool shell). Missing identity blocks. `acquire --source <plugin> --owner-pid <pid>` must succeed; no partial helpers/alternate versions.
3. Retain `lease`, `bundle`, `skillRoot`, `digest`. Reload the pinned entry; resolve every later reference/helper/import there. Preserve checkpoint locations, authority and budgets.
4. Each consumer (worker/successor/gate) leases the passed bundle with its host PID before acknowledgement/helper use. Sender holds lease until receiver acquisition; never forward cache paths.
5. Pinned helper: `collect --limit 3` after acquisition; at completion/cancellation/blocked hand-back, `release --lease <lease>` only your lease, then collect. Live PID/start identities retain bundles; failed probes stop cleanup.

Store: `${XDG_DATA_HOME:-$HOME/.local/share}/sai/ship-it/plugin-pins`; forward explicit `--store` unchanged. Complete plugin/manifests/inventory/source path publish atomically under lock; interruptions preserve bundles. Provider cleanup is external.
