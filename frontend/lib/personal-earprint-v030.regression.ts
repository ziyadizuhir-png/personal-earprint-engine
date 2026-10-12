import { generateV030, parsePeq, reconstructPeq, type Curve } from "./personal-earprint-v030";

/** Browser-console regression vectors for the canonical v0.3.0 path. */
export function runV030Regression(): void {
  const frequencies = [20, 999, 1000, 11200, 11600, 12000, 20000];
  const base: Curve = { frequency_hz: frequencies, level_db: [1, 2, 3, 4, 5, 6, 7] };
  const input = { id: "fixture", measurement: base, preferred: "# SoundEQ Dore\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\nHS, 8000, -2, 0.7" };
  const result = generateV030(base, [input]);
  const final = result.final_target.level_db;
  for (const index of [0, 1, 5, 6]) if (final[index] !== base.level_db[index]) throw new Error("Base ownership changed outside the personal domain");
  if (Math.abs(final[4] - base.level_db[4]) >= Math.abs(final[3] - base.level_db[3])) throw new Error("11.2–12 kHz taper is not monotone toward Base Target");
  if (result.grid.master_frequency_hz.length !== result.grid.represented_frequency_hz.length || result.grid.clipped) throw new Error("complete fixture grid was unexpectedly clipped");
  if (parsePeq(input.preferred).length !== 2 || !reconstructPeq(input.preferred, frequencies).level_db.every(Number.isFinite)) throw new Error("PEQ parser/reconstruction regression");
}
