# Personal EarPrint Engine v0.3.1

This repository implements the uploaded `Personal_EarPrint_v0.3.1_bundle.zip` as its sole production authority.

The pipeline keeps the nine bundled FR/PEQ pairs, reconstructs each active PK PEQ as a 48 kHz digital biquad, normalizes FR, PEQ response, and Base Target at 1 kHz, and computes `FR + PEQ - Base`. It combines all nine deltas pointwise with median, raw MAD, and Huber IRLS (`c=1.345`, scale floor `0.1 dB`, tolerance `1e-8`, maximum 100 iterations).

The final target owns the exact Base below 1 kHz and at/above 12 kHz, applies the full robust Delta from 1–11.2 kHz, and uses only a C1 smoothstep taper from 11.2–12 kHz. No fixed 8.1275 kHz attenuation, global smoothing, or final normalization is applied. Broad/local and narrow-peak outputs are diagnostics only.

The API exposes Base Target listing/detail/export/delete, IEM import/listing, Robust Target generation/export/detail, and persisted Robust Target history. Generation requires exactly the nine distinct bundled IEM IDs and returns the final curve, intermediate stages, provenance hashes, validation, and diagnostics. Generated names are derived from the selected Base Target name with one trailing ` Robust` suffix.

## Verification

```text
python -m pytest
cd frontend
pnpm install --frozen-lockfile
pnpm run build
```

The retired v0.3.0/V4.4 implementation is not imported by production routes or the v0.3.1 engine. Existing V4.4-origin Base Target records remain available as clearly marked reference inputs so user data is preserved; their provenance is never presented as v0.3.1 engine output.
