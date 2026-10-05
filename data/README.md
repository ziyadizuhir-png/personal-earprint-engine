# Runtime data

These directories hold local or mounted deployment data and are intentionally
not committed:

- `iems/` — imported IEM measurements and PEQ files
- `base-targets/` — uploaded Base Targets
- `targets/` — uploaded custom targets

Only these placeholder files are tracked so a fresh checkout has the documented
layout. Keep real uploads out of Git; configure `DATA_ROOT` for production.
