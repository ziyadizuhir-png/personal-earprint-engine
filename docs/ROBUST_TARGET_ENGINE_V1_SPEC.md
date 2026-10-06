# Dynamic Robust Target Engine v1

This is the active production specification. Historical V4.4 documents are
research/provenance records and are not separate production engines.

The pipeline is: validate inputs -> select Base Target master grid -> exact
1000 Hz normalization -> digital-biquad PEQ reconstruction -> Desired Response
-> Personal Delta -> median/MAD/consensus diagnostics -> deterministic Huber
center -> local safety analysis -> Robust Target.

Ownership is exact: below 1 kHz Base; 1–10 kHz full robust delta; 10–12 kHz
half robust delta; 12–14 kHz cubic Hermite C1 handoff to zero delta; at and
above 14 kHz exact Base. The final curve is never globally renormalized.

The canonical curve is the mathematical authority. External text export, when
provided, is a separate deterministic serialization and is never fed back into
generation. No PEQ filter list is a Robust Target output.
