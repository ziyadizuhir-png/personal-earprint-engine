# ZUHIR Personal Earprint V4.4 — Backbone Reference

> Superseded for mathematical authority by `docs/ZUHIR_PERSONAL_EARPRINT_V4.4_FINAL_LOCKED_SPEC.md`.

## Target modes

Exactly two:

1. Robust Target
2. Pure EarPrint

Excluded:

- Hybrid Graph
- Hybrid Graph as a selectable target mode
- Third hybrid target mode
- Old Adaptive Handoff architecture

## Base Target

Default:

Headphones.com IEM DF (B105 + 8 dB)

## Master Grid

Base Target grid.

Interpolation: log-frequency.

## Normalization

Exact 1000 Hz calculation anchor.

Final target is not globally renormalized.

## Frequency ownership

- < 1 kHz: Base Target
- 1–12 kHz: Personal / Robust EarPrint
- 12–14 kHz: linear personal-to-base fade
- > 14 kHz: Base Target

For 12–14 kHz:

w(f) = (14000 - f) / 2000

Target(f) = BaseTarget(f) + DeltaSafe(f) * w(f)

## Aggregation

Median primary estimator.

MAD:

median(abs(Delta_i - Delta_median))

Consensus epsilon:

0.25 dB

n+ = count(Delta_i > +0.25)

n- = count(Delta_i < -0.25)

n0 = count(abs(Delta_i) <= 0.25)

## Important

The exact formulas for G, C, Broad, Local, Feature Classification, and Delta Safe are not locked here.
Implementation must not invent them.
