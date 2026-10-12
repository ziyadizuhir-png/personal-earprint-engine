# Personal EarPrint v0.3.1 contract

This document mirrors the controlling uploaded bundle. The canonical Base Target is `Headphones.com IEM DF (Tilt -1 dB/oct, B105 5 dB)` and the canonical dataset is the nine bundled FR/PEQ pairs.

For every IEM, interpolate on log frequency, normalize FR, reconstructed 48 kHz digital PK response, and Base Target independently at 1 kHz, then compute:

`D_i(f) = normalized_FR_i(f) + normalized_PEQ_i(f) - normalized_Base(f)`

Aggregate pointwise with median, raw MAD, and Huber IRLS using `c=1.345`, `max(1.4826*MAD, 0.1 dB)`, `1e-8 dB` convergence tolerance, and a 100-iteration cap. All nine IEMs remain in the calculation; consensus counts and MAD are diagnostics.

The master grid is the Base Target grid plus exact 1,000 Hz, 11,200 Hz, and 12,000 Hz boundary points. The final curve is exact Base below 1 kHz and at/above 12 kHz, Base plus the full robust Delta from 1–11.2 kHz, and Base plus a C1 cubic smoothstep taper from 11.2–12 kHz. There is no fixed 8.1275 kHz attenuation, global smoothing, or final normalization. Broad/local smoothing and narrow peak detection are diagnostics only.
