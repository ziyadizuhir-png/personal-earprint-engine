# ZUHIR PERSONAL LISTENER / EARPRINT
## V4.4 — FINAL UNIVERSAL PERSONAL TARGET — LOCKED SPEC

**Authority:** User-provided V4.4 Final Universal Personal Target Experiment specification in the project conversation.

**Status:** LOCKED for the V4.4 experiment. Do not replace with legacy formulas or silently invent missing mathematics.

## 1. Objective

Build one universal personal target for AutoEQ that:

- preserves personal earprint from SoundEQDore sine-sweep;
- does not depend on one IEM;
- never averages raw IEM FRs;
- is robust to outliers;
- does not discard a personal feature merely because a curve looks unusual;
- produces a natural target across multiple IEMs;
- produces practical device correction without sacrificing personal shape.

Priority:

**PERSONAL + ROBUST + NATURAL + CONSISTENT**

AutoEQ practicality is a secondary constraint, not the primary objective.

## 2. Dataset

Use exactly these nine IEM votes for the V4.4 reference experiment:

1. FOCUS Vocal
2. 7Hz Timeless
3. HIFIMAN Svanar Wireless Jr
4. ROSESELSA Ceramics Ultra
5. TForce Yuan Li
6. Sony WF-1000XM4
7. Samsung Galaxy Buds2 Pro (passive mode)
8. 7Hz Salnotes Zero 2
9. MOONDROP PUDDING

Each IEM provides:

- measured FR (711)
- SoundEQDore sine-sweep PEQ

Do not average raw FRs.
Do not average PEQ gains.

The combined object is:

Measured FR + reconstructed preferred PEQ -> Desired Response -> Personal Delta -> Robust aggregation.

## 3. Base Target

Default Base Target:

**Headphones.com IEM DF (B105 + 8 dB)**

The Base Target is a tonal reference framework, not personal preference.

Personal Delta:

`Personal Delta = Desired Response - Base Target`

## 4. Master Frequency Grid and Ownership

The Base Target frequency grid is the Master Grid.
All curves are interpolated onto the Master Grid in log-frequency space.

Exact 1000 Hz is the normalization/calculation anchor.

Ownership:

- `< 1 kHz` -> Base Target
- `1–12 kHz` -> Personal EarPrint / Robust Personal Delta
- `12–14 kHz` -> Personal-to-Base linear fade
- `> 14 kHz` -> Base Target

For 12–14 kHz:

`w(f) = (14000 - f) / 2000`

`FinalTarget(f) = BaseTarget(f) + DeltaSafe(f) * w(f)`

No final global renormalization.

The 1 kHz boundary is an ownership boundary, not a permission to create a kink.

## 5. Normalization

For every IEM measurement:

`M_i'(f) = M_i(f) - M_i(1000)`

For reconstructed SoundEQDore response:

`PEQ_i'(f) = PEQ_i(f) - PEQ_i(1000)`

1 kHz removes absolute measurement-level differences and is only the calculation reference.

Do not renormalize the final target globally.

## 6. SoundEQDore Reconstruction

Reconstruct every PEQ filter as a continuous digital-biquad magnitude response.

Supported filter types:

- PK
- HS
- LS

Default sample rate: 48000 Hz.

Combine filter magnitudes in dB, then normalize the combined PEQ response at exactly 1000 Hz.

Desired Response:

`D_i(f) = M_i'(f) + PEQ_i'(f)`

Desired Response is the primary preference data, not raw FR and not PEQ gain lists.

## 7. Personal Delta

For each IEM:

`Delta_i(f) = D_i(f) - B'(f)`

where `B'` is the normalized Base Target.

## 8. Robust Aggregation

Primary estimator:

`Delta_median(f) = median(Delta_1 ... Delta_9)`

Dispersion:

`MAD(f) = median(|Delta_i(f) - Delta_median(f)|)`

MAD is an uncertainty/dispersion indicator.

High MAD is NOT an automatic delete rule.

## 9. Directional Consensus — LOCKED

Use:

`epsilon = 0.25 dB`

At each frequency:

`n+ = count(Delta_i > +0.25 dB)`

`n- = count(Delta_i < -0.25 dB)`

`n0 = count(|Delta_i| <= 0.25 dB)`

`Nactive = n+ + n-`

Directional agreement:

`C = max(n+, n-) / Nactive`

Directional margin:

`G = |n+ - n-| / Nactive`

When `Nactive = 0`, `G = 0`.

**Important:**

- `C` is directional agreement.
- `G` is directional margin.
- Neither `C` nor `G` may be silently redefined as `1-MAD`, generic confidence, or a global multiplier.
- `G` must not scale down the whole median delta.

## 10. Broad / Local Separation — LOCKED ANALYSIS MODEL

Use approximately **1/12 octave** as the broad/local analysis separation.

`BroadShape = smooth(Delta_median)`

`LocalDetail = Delta_median - BroadShape`

This separation is an analysis tool only.

It is NOT permission to globally smooth the final target.

No global smoothing is allowed.

## 11. Feature Classification — LOCKED RULE SET

Each feature is evaluated using:

- amplitude
- bandwidth
- directional agreement
- MAD
- local curvature
- frequency region
- broad vs narrow character
- consistency across all nine IEMs

Rules:

### Broad + High Agreement
Preserve.

### Broad + Low Agreement
Evaluate MAD and cross-IEM consistency.

### Narrow + High Agreement
Preserve shape, then check practicality.

### Narrow + Low Agreement
Reduce/suppress locally.

### High MAD + Narrow
Treat as an unstable candidate.

Never automatically delete merely because a curve looks unusual.

## 12. Frequency-Specific Priorities

### 2–4 kHz
Preservation priority because of vocal/presence importance.

This is a priority, not an unconditional lock. Inconsistency across the nine-IEM data may justify local reduction.

### Around 6 kHz
A broad personal feature around approximately 5.7–6.4 kHz may be preserved when supported by the robust median and cross-IEM evidence.

Do not flatten the entire region because individual IEM corrections are different.

Interpretation:

Different IEM FR -> different device correction -> common personal tonal destination.

### 7–10 kHz
Preserve broad personal upper-treble shape.
Do not bake device-specific narrow micro-features into a universal target.

### 10–12 kHz
Confidence is lower than 1–6 kHz.
Preserve broad shape while reducing unstable micro-detail.
Do not flatten the region globally.

## 13. V4.4 Natural-Target-First Behavior

V4.4 is intended to be less conservative than V4.3 in the upper-treble.

The historical V4.4 experiment used controlled restoration in approximately:

`7.5–10.2 kHz`

with the purpose of retaining broad personal upper-treble shape without restoring aggressive earlier-V4 micro-detail.

**Critical reproducibility rule:** the phrase above is an experimental behavior description, not a complete numeric restoration formula. Do not invent a new restoration percentage, curve, or interpolation rule and call it V4.4.

For exact numerical reproduction, the original V4.4 golden target/output must be frozen and regression-tested.

## 14. Delta Safe — LOCKED PRINCIPLE

Default:

`Delta_safe = Delta_median`

Only modify `Delta_safe` locally when there is clear evidence of one or more of:

1. high-Q instability
2. excessive correction
3. narrow unsupported feature
4. obvious AutoEQ impracticality
5. strong dispersion + weak consensus

Broad and stable personal features remain:

`Delta_safe = Delta_median`

No global attenuation formula may be invented.

Do not implement:

`Delta_safe = Delta_median * C`

or:

`Delta_safe = Delta_median * G`

or any equivalent blanket shrinkage.

Local safety must modify only the justified local component.

## 15. Local Safety Principle

When a correction looks unnatural:

Identify local feature
-> trace it back to the target feature
-> check MAD, consensus, bandwidth, curvature, cross-IEM support
-> modify only the local component if justified.

Never apply a global 6–12 kHz flattening operation.

## 16. Final Target

The conceptual personal target is:

`T_personal(f) = B(f) + Delta_median(f)`

The final V4.4 target is:

`T_V4.4(f) = B(f) + Delta_safe(f)`

subject to the locked frequency ownership rules.

Because `Delta_safe = Delta_median` by default, the normal path preserves the robust personal delta.

## 17. AutoEQ

AutoEQ is secondary validation only.

Order:

SoundEQDore
-> Desired Response
-> Personal Delta
-> 9-IEM Robust Median
-> V4.4 Personal Target
-> AutoEQ
-> device-specific correction

AutoEQ results must never modify the target authority.

Red flags are diagnostic only:

- extremely high Q
- extreme gain
- multiple overlapping filters
- very narrow correction
- alternating boost/cut
- excessive preamp

A red flag is not an automatic target failure.

## 18. Explicit Prohibitions

Do not use:

- Harman blending
- RTINGS blending
- Sonarworks blending
- Hybrid Graph
- Hybrid Target
- raw-IEM averaging
- PEQ-gain averaging
- global smoothing
- global 6–12 kHz flattening
- automatic deletion because MAD is high
- automatic deletion because a curve looks strange
- target optimization based on one IEM
- final global renormalization
- legacy Adaptive Handoff
- old hybrid target logic
- historical Huber logic as a replacement for current V4.4 Delta Safe unless explicitly re-authorized

## 19. Validation Acceptance Criteria

V4.4 is accepted when:

1. Personal shape remains clearly visible.
2. Broad earprint is not erased.
3. Narrow unstable features do not dominate.
4. Target behaves naturally across the nine IEMs.
5. One IEM cannot dominate the target.
6. 1–4 kHz remains coherent.
7. 4–6 kHz remains personal.
8. 6–10 kHz remains personal without becoming artificial.
9. 10–12 kHz is conservative but not flattened.
10. 12–14 kHz is smooth.
11. 1 kHz boundary is clean.
12. No artificial kink is introduced.
13. Target remains measurably different from generic reference targets.
14. Device correction varies naturally according to each IEM FR.

## 20. Determinism / Exact-Result Lock

The engine must be deterministic for identical:

- nine source FR files
- nine SoundEQDore PEQ files
- Base Target
- sample rate
- interpolation rules
- normalization anchor
- frequency ownership
- V4.4 configuration
- engine version

To claim **exact same numerical result as an existing V4.4 run**, the historical V4.4 final target file must be stored as a golden reference and compared point-by-point (preferably SHA-256 plus max absolute dB error).

No prose description, including the 7.5–10.2 kHz restoration sentence, is sufficient to guarantee bit-for-bit identity without that golden output.

## 21. Final Philosophy

Do not optimize the target so that it looks visually pretty.

Optimize it so that it remains:

**PERSONAL + ROBUST + NATURAL + CONSISTENT**

The target is a universal personal destination extracted from repeated sine-sweep preference behavior across different IEMs, not a generic reference curve.
