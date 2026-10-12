# Personal EarPrint Studio v0.3.0 Traceability Matrix

Audit date: 2026-10-12  
Authority: `docs/PERSONAL_EARPRINT_STUDIO_V0.3.0_SPEC.md`  
Legacy reference only: `docs/V44_SPEC.md`, `docs/ZUHIR_PERSONAL_EARPRINT_V4.4_FINAL_LOCKED_SPEC.md`, and the `engine/v44/` compatibility modules.

## Formula and ownership traceability

| Requirement | Canonical implementation/evidence | Status | Notes |
|---|---|---|---|
| 1 kHz normalization | `frontend/lib/personal-earprint-v030.ts`: `normalized()`, `atAnchor()`, `ANCHOR_HZ = 1000` | PASS | Measurement, reconstructed PEQ, and Base Target are normalized independently. Exact 1 kHz coverage is required. |
| Log-frequency interpolation | `interpolateLog()` in the browser solver; `engine/v44/v44.py` compatibility equivalent | PASS | The browser grid is clipped to common covered measurement range; it does not extrapolate. |
| 48 kHz RBJ PEQ reconstruction | `biquadResponse()` and `reconstructPeq()` in the browser solver | PASS | PK, HS, and LS are reconstructed as digital biquads at `SAMPLE_RATE_HZ = 48000`. |
| PEQ response summation and normalization | `generateV030()` | PASS | Filter magnitudes are summed in dB, then the combined response is normalized at 1 kHz. |
| `D_i = M_i' + PEQ_i'` | `generateV030()` `desired` value | PASS | No alternate server-side solver is used by the v0.3.0 UI. |
| `Delta_i = D_i - B'` | `generateV030()` `delta` value | PASS | Uses normalized Base Target on the common grid. |
| Pointwise median center | `median_delta` in `generateV030()` | PASS | Exact pointwise median across selected IEM deltas. |
| MAD diagnostic | `mad` in `generateV030()` | PASS | Pointwise median absolute deviation; not used as an unrequested smoothing or weighting transform. |
| Consensus epsilon 0.25 dB | `EPSILON_DB = 0.25` and `n_plus/n_minus/n_zero` | PASS | Diagnostic classification only; it does not multiply or suppress the target. |
| Robust estimator wording | Canonical spec § Numerical pipeline; browser solver | PARTIAL | The executable contract defines median + MAD diagnostics. Any stronger estimator semantics remain unresolved and are not invented. |
| Base owns below 1 kHz | `final_target` ownership branch | PASS | Final target returns the Base Target below 1 kHz. |
| Personal delta owns 1–11.2 kHz | `final_target` ownership branch | PASS | Median delta is applied directly in this interval. |
| Smooth taper 11.2–12 kHz | `final_target` cubic smoothstep | PARTIAL | Cubic smoothstep is the documented fallback because the source artifact only says “smooth taper”. The choice is surfaced in diagnostics. |
| Base resumes at/above 12 kHz | `final_target` ownership branch | PASS | Final target returns the Base Target at and above 12 kHz. |
| No default 8.1275 kHz notch | No notch code; solver warning and tests | PASS | No global safety attenuation or global smoothing is applied. |
| No global renormalization | `final_target` construction | PASS | The output preserves the Base Target outside the personal domain. |
| Target ownership/taper | UI ownership facts and result legend | PASS | The workflow visibly communicates the three frequency regions. |
| PEQ solver location | `GET /api/robust-targets/inputs` + browser `generateV030()` | PASS | Backend stores/serves source data; TypeScript owns PEQ solving. |
| Anti-overfit PEQ fitting | `frontend/lib/peq-solver-v030.ts` + `docs/PEQ_SOLVER_ANTI_OVERFIT.md` | PASS / SPEC BLOCKED thresholds | Optional solver keeps canonical target math unchanged; evidence-gates narrow candidates, combines pointwise/ERB/shape/topology/stability objectives, simulates quantization, stops deterministically, rolls back to best state, and caps allocation at 10 bands. Numeric fitting controls have no v0.3.0 source values and remain configured SPEC BLOCKED defaults. |

## Architecture, storage, and deployment

| Area | Evidence | Status | Notes |
|---|---|---|---|
| Source-data API | `backend/app/main.py`, `backend/app/robust_target.py` | PASS | IEMs, Base Targets, health, imports, and browser-input delivery are exposed. |
| Prepared source validation | `backend/app/ingest.py`, `validate_preferred()` | PASS | Invalid or missing PEQ is surfaced as a non-ready library item. |
| Persistent storage boundary | `backend/app/storage.py`, `docs/DEPLOYMENT.md`, `render.yaml` | PASS | Filesystem storage requires a persistent `DATA_ROOT`; the deployment docs call out the limitation. |
| Provenance and artifact identity | `backend/app/robust_target.py` | PASS | Compatibility generation hashes selected measurements, preferred PEQ, and Base Target. |
| Static frontend deployment | `frontend/next.config.js`, `.github/workflows/pages.yml` | PASS | GitHub Pages export is configured; live data still requires the backend. |
| CI verification | `.github/workflows/verify.yml` | PARTIAL | Workflow covers Python compile/tests and frontend build, but local verification is unavailable without Python/pytest. |
| GitHub Actions health | `.github/workflows/*.yml` | UNVERIFIED | Workflow files were inspected; remote Actions run history/status was not available in the local checkout. |
| Legacy V4.4 backend route | `backend/app/v44.py`, `engine/v44/` | SPEC BLOCKED | Retained as compatibility/audit material. It must not be treated as the v0.3.0 browser contract. |
| Feature Classification | Canonical spec § Explicitly unresolved | SPEC BLOCKED | No executable thresholds were provided, so the UI labels it rather than fabricating a result. |

## Verification record

- PASS — repository inspection confirmed the active frontend imports `generateV030` and requests `/api/robust-targets/inputs`.
- PASS — seeded data and deployment configuration are present in the repository.
- PASS — Python bytecode compilation completed for `backend/app`, `engine`, and `tests`.
- PASS — the v0.3.0 and engine contract test functions were executed directly with the bundled Python runtime; the stale 12 kHz expectation was corrected to the canonical ownership rule.
- PARTIAL — the full pytest runner and frontend production build were not completed in this environment: pytest is not installed, and pnpm cannot resolve the sandbox-managed `frontend/node_modules` directory.
- UNVERIFIED — remote GitHub Actions status and deployed backend health require access to the GitHub/hosting control planes.
