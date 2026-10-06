# Engine Reconciliation Report

## Scope

The active production path is `engine.robust_target.generate_robust_target`,
which delegates to the single canonical implementation in
`engine/v44/v44.py`. No second mathematical pipeline was introduced.

## Files changed in this reconciliation

- `engine/v44/v44.py` — active Personal Earprint formula stages, local safety,
  diagnostics, and Hermite handoff.
- `engine/v44/classification.py` — only Feature Classification remains
  unresolved.
- `engine/v44_engine.py` — compatibility import surface was audited and
  remains routed to the canonical engine; no duplicate implementation was
  added.
- `backend/app/v44.py` — API stage status now matches the canonical engine.
- `backend/app/robust_target.py` — canonical artifacts now include all
  intermediate stages, active IEM provenance, and a dataset revision.
- `backend/tests/test_v44_api.py` and `tests/test_v44_engine.py` — regression
  coverage for the active formula and its production status.
- `ENGINE_RECONCILIATION_REPORT.md` — this report.

The repository Base Target resource used is
`data/base-targets/jm-1-df-tilt-0-8-db-oct-b105-5-db`, with metadata name
`JM-1 DF (Tilt -0.8 dB/oct, B105 5 dB)`.

## Formula status

| Stage | Status |
|---|---|
| 1 kHz normalization | PASS |
| Exact PK/LS/HS biquad reconstruction | PASS |
| Desired Response | PASS |
| Personal Delta | PASS |
| Huber center, c=1.345 | PASS |
| MAD scale, 1.4826 | PASS |
| Consensus epsilon, 0.25 dB | PASS |
| Local 8.13 kHz safety | PASS |
| 1–10 kHz ownership | PASS |
| 10–12 kHz ownership | PASS |
| 12–14 kHz Hermite handoff | PASS |
| <1 kHz and >=14 kHz Base ownership | PASS |
| Dynamic IEM votes | PASS |
| JM-1 default Base Target | PASS |

Broad and Local are diagnostics. Feature Classification remains explicitly
specification-blocked because no executable classification thresholds were
provided. The PEQ solver is not part of this product.

## Legacy blockers fixed

- The active backend path already routes through
  `engine.robust_target.generate_robust_target`; it now executes the
  canonical Personal Earprint implementation rather than an alternate
  generator.
- The API no longer reports Broad and Local as unresolved after their
  deterministic diagnostic stages are computed.
- The old test expectation that Broad must remain unresolved was updated to
  assert the actual production contract; Feature Classification remains the
  explicit blocker.
- Dataset identity is included in the generated artifact hash and revision,
  so changing the selected IEM vote set cannot silently reuse the same
  provenance identity.

## API/UI alignment

The canonical API remains `POST /api/robust-targets/generate`. It returns the
full engine result under `intermediate`, including normalized curves, PEQ
reconstruction, Desired Response, Personal Delta, median/MAD, n+/n-/n0, G, C,
Broad, Local, Feature Classification, Delta Safe, and Final Target. The UI
continues to present Robust Target as the production target and keeps the
Feature Classification stage visibly unavailable rather than fabricating it.

## Data/default blocker

The Base Target failure was caused by default discovery not accepting the
canonical JM-1 target identity through the merged data-root discovery path.
Resolution now recognizes the exact canonical slug
`jm-1-df-tilt-0-8-db-oct-b105-5-db` while preserving fail-closed temporary-root
overrides.

## Verification

Frontend production build previously passed. Backend pytest execution remains
unverified in this workspace because Python/pytest is not installed; no green
test result is claimed here. The required commands are:

```text
pytest backend/tests
pytest tests/test_v44_engine.py
```

No PEQ solver was reintroduced.

## PEQ ingestion reconciliation

Every IEM continues to use the attached record layout:
`measurement_source.txt`, `measurement.csv`, `preferred.txt`, and
`metadata.json`. The canonical `parse_peq()` validator now accepts the
SoundEQ Dore PK/HS/LS forms used by the seeded records, counts filters, and
rejects malformed filter lines instead of silently producing an empty PEQ.
Both `/api/iems` and `/api/v44/iems` report `peq_valid`,
`peq_filter_count`, `peq_source`, and readiness. Generation reads that same
`preferred.txt` through `_iem()` and blocks missing or invalid PEQ data.

Robust Target provenance now hashes each selected IEM's prepared measurement
and `preferred.txt`, together with the Base Target hash. Changing an attached
PEQ therefore changes the dataset revision and target identity. Integration
tests cover upload storage, exact reconstructed biquad response, PEQ changes,
and missing/malformed preferred files.
