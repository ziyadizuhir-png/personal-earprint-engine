# PEQ solver anti-overfit contract

The canonical v0.3.0 target remains unchanged. `generateV030()` still performs
the specified reconstruction, pointwise median/MAD diagnostics, ownership
window, and 11.2–12 kHz taper. This document applies only to the optional
browser-side PEQ fitting layer in `frontend/lib/peq-solver-v030.ts`.

The user-provided graph is evidence of a failure mode: a solver that minimizes
pointwise error alone can spend one filter on each narrow treble ripple. The
solver therefore requires local evidence before considering a high-Q candidate,
and scores candidates using pointwise error plus ERB-bin error, log-frequency
slope, curvature, topology, and a high-Q stability penalty. Candidate responses
are quantized/export-simulated before acceptance. Search order is deterministic;
the best accepted state is retained, fitting stops on no improving candidate or
the configured iteration limit, and the hard allocation cap is 10 bands.

## Specification status

v0.3.0 explicitly supplies 48 kHz reconstruction and the canonical target
ownership rules. It does not supply numeric thresholds for high-Q evidence,
objective weights, quantization, candidate-Q values, or early stopping. Those
values are therefore **SPEC BLOCKED** and are exposed through
`PeqSolverConfig`. `SPEC_BLOCKED_SOLVER_DEFAULTS` is a proposed tunable default
set for experiments and regression tests; it is not canonical target math.

The anti-overfit regression requirement is: a target containing broad tonal
change plus many narrow treble ripples must not produce one filter per ripple.
The regression should assert the 10-band cap, deterministic output,
quantization-safe response, and that narrow candidates are rejected when local
support is below the configured evidence gate.
