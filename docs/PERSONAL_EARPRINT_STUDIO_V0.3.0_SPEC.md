# Personal EarPrint Studio v0.3.0 — Canonical Specification

This is the repository's canonical mathematical contract. The existing V4.4
documents and modules are retained as legacy material for audit only; they are
not an authority for v0.3.0 behavior.

## Scope and ownership

- The initial experiment is exactly the nine IEM pairs already stored in
  `data/iems/`: FOCUS Vocal, 7Hz Timeless, HIFIMAN Svanar Wireless Jr,
  ROSESELSA Ceramics Ultra, TForce Yuan Li, Sony WF-1000XM4, Samsung Galaxy
  Buds2 Pro passive mode, 7Hz Salnotes Zero 2, and MOONDROP PUDDING.
- The Base Target owns frequencies below 1 kHz and at or above 12 kHz.
- The personalized delta owns 1–11.2 kHz.
- The personalized delta tapers smoothly to zero from 11.2–12 kHz.
- There is no default 8.1275 kHz safety notch or any other global safety
  attenuation in the v0.3.0 canonical path.
- The Base Target is exact outside the personalized domain. The final output
  is not globally renormalized.

## Numerical pipeline

For each IEM, on the Base Target master grid:

1. Interpolate measurement and PEQ response by linear interpolation in
   log-frequency.
2. Normalize measurement, reconstructed PEQ, and Base Target independently at
   exactly 1 kHz.
3. Reconstruct every SoundEQDore PK/HS/LS filter as a digital biquad at 48 kHz;
   sum filter magnitudes in dB, then normalize the combined response at 1 kHz.
4. Compute `D_i = normalized_measurement_i + normalized_reconstructed_PEQ_i`.
5. Compute `delta_i = D_i - normalized_base`.
6. Aggregate the nine deltas with the v0.3.0 robust estimator. The current
   executable contract uses pointwise median plus MAD diagnostics and does not
   apply Huber weighting or a blanket consensus multiplier.

The browser TypeScript module in `frontend/lib/personal-earprint-v030.ts` is
the executable reference for PEQ reconstruction and target construction. The
server stores and serves source data and generated artifacts; it does not own
the PEQ solver.

## Explicitly unresolved

The v0.3.0 source artifact available to this recovery task did not expose a
more specific taper equation than “smooth taper”. The implementation uses the
standard cubic smoothstep `1 - (3t² - 2t³)` on 11.2–12 kHz and labels that
choice in diagnostics. If the original v0.3.0 artifact specifies another
window, replace only that function and its regression vectors.
