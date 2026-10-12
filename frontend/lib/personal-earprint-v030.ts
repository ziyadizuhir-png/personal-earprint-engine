export type Curve = { frequency_hz: number[]; level_db: number[] };
export type PeqFilter = { kind: "PK" | "HS" | "LS"; frequency_hz: number; gain_db: number; q: number };
export type V030Input = { id: string; measurement: Curve; preferred: string };
export type V030Result = {
  normalized_base: Curve;
  per_iem: Record<string, { normalized_measurement: Curve; reconstructed_peq: Curve; normalized_peq: Curve; desired_response: Curve; delta: Curve }>;
  median_delta: Curve;
  mad: Curve;
  final_target: Curve;
  grid: { master_frequency_hz: number[]; represented_frequency_hz: number[]; clipped: boolean };
  diagnostics: { n_plus: number[]; n_minus: number[]; n_zero: number[]; warnings: string[] };
};

const ANCHOR_HZ = 1000;
const SAMPLE_RATE_HZ = 48000;
const EPSILON_DB = 0.25;
const NUMBER = "[-+]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][-+]?\\d+)?";
const FILTER = new RegExp(`(?:Filter\\s*\\d+\\s*:\\s*)?(?:ON\\s+)?(PK|HS|LS)\\s*(?:Fc\\s*)?(${NUMBER})\\s*(?:Hz)?\\s*(?:Gain\\s*)?(${NUMBER})\\s*(?:dB)?\\s*(?:Q\\s*)?(${NUMBER})`, "i");

function assertCurve(c: Curve): void {
  if (c.frequency_hz.length !== c.level_db.length || c.frequency_hz.length < 2) throw new Error("curve arrays must match and contain at least two points");
  for (let i = 0; i < c.frequency_hz.length; i++) {
    if (!Number.isFinite(c.frequency_hz[i]) || !Number.isFinite(c.level_db[i]) || c.frequency_hz[i] <= 0 || (i && c.frequency_hz[i] <= c.frequency_hz[i - 1])) throw new Error("curve must be finite and strictly ascending");
  }
}

function interpolateLog(source: Curve, frequency_hz: number[]): number[] {
  assertCurve(source);
  return frequency_hz.map((f) => {
    if (f < source.frequency_hz[0] || f > source.frequency_hz[source.frequency_hz.length - 1]) throw new Error("source curve does not cover master grid");
    let hi = source.frequency_hz.findIndex((x) => x >= f);
    if (hi <= 0) return source.level_db[0];
    if (source.frequency_hz[hi] === f) return source.level_db[hi];
    const lo = hi - 1;
    const t = (Math.log(f) - Math.log(source.frequency_hz[lo])) / (Math.log(source.frequency_hz[hi]) - Math.log(source.frequency_hz[lo]));
    return source.level_db[lo] + t * (source.level_db[hi] - source.level_db[lo]);
  });
}

function atAnchor(c: Curve): number { return interpolateLog(c, [ANCHOR_HZ])[0]; }
function normalized(c: Curve): Curve { const anchor = atAnchor(c); return { frequency_hz: [...c.frequency_hz], level_db: c.level_db.map((v) => v - anchor) }; }

export function parsePeq(text: string): PeqFilter[] {
  const filters: PeqFilter[] = [];
  for (const [index, raw] of text.split(/\r?\n/).entries()) {
    const line = raw.trim();
    if (!line || /^(#|\/\/|;)/.test(line) || /^(soundeq dore|device:|generated:|preamp:|channel:|sample rate:|format:|author:|notes:)/i.test(line)) continue;
    const match = FILTER.exec(line) ?? (() => { const p = line.split(",").map((x) => x.trim()); return p.length === 4 && /^(PK|HS|LS)$/i.test(p[0]) ? [line, p[0], p[1], p[2], p[3]] : null; })();
    if (!match) throw new Error(`Malformed or unsupported PEQ filter on line ${index + 1}`);
    const item = { kind: match[1].toUpperCase() as PeqFilter["kind"], frequency_hz: Number(match[2]), gain_db: Number(match[3]), q: Number(match[4]) };
    if (![item.frequency_hz, item.gain_db, item.q].every(Number.isFinite) || item.frequency_hz <= 0 || item.q <= 0) throw new Error(`Invalid PEQ filter on line ${index + 1}`);
    filters.push(item);
  }
  if (!filters.length) throw new Error("PEQ contains no PK, HS, or LS filters");
  return filters;
}

function biquadResponse(filter: PeqFilter, frequency_hz: number[]): number[] {
  const A = 10 ** (filter.gain_db / 40), w0 = 2 * Math.PI * filter.frequency_hz / SAMPLE_RATE_HZ, alpha = Math.sin(w0) / (2 * filter.q), c = Math.cos(w0);
  let b0: number, b1: number, b2: number, a0: number, a1: number, a2: number;
  if (filter.kind === "PK") { b0 = 1 + alpha * A; b1 = -2 * c; b2 = 1 - alpha * A; a0 = 1 + alpha / A; a1 = -2 * c; a2 = 1 - alpha / A; }
  else if (filter.kind === "HS") { b0 = A * ((A + 1) + (A - 1) * c + 2 * Math.sqrt(A) * alpha); b1 = -2 * A * ((A - 1) + (A + 1) * c); b2 = A * ((A + 1) + (A - 1) * c - 2 * Math.sqrt(A) * alpha); a0 = (A + 1) - (A - 1) * c + 2 * Math.sqrt(A) * alpha; a1 = 2 * ((A - 1) - (A + 1) * c); a2 = (A + 1) - (A - 1) * c - 2 * Math.sqrt(A) * alpha; }
  else { b0 = A * ((A + 1) - (A - 1) * c + 2 * Math.sqrt(A) * alpha); b1 = 2 * A * ((A - 1) + (A + 1) * c); b2 = A * ((A + 1) - (A - 1) * c - 2 * Math.sqrt(A) * alpha); a0 = (A + 1) + (A - 1) * c + 2 * Math.sqrt(A) * alpha; a1 = -2 * ((A - 1) + (A + 1) * c); a2 = (A + 1) + (A - 1) * c - 2 * Math.sqrt(A) * alpha; }
  return frequency_hz.map((f) => { const z = { re: Math.cos(-2 * Math.PI * f / SAMPLE_RATE_HZ), im: Math.sin(-2 * Math.PI * f / SAMPLE_RATE_HZ) }; const z2 = { re: z.re * z.re - z.im * z.im, im: 2 * z.re * z.im }; const nr = b0 + b1 * z.re + b2 * z2.re, ni = b1 * z.im + b2 * z2.im, dr = a0 + a1 * z.re + a2 * z2.re, di = a1 * z.im + a2 * z2.im; return 20 * Math.log10(Math.max(Math.hypot(nr, ni) / Math.hypot(dr, di), 1e-300)); });
}

export function reconstructPeq(text: string, frequency_hz: number[]): Curve { const level_db = frequency_hz.map(() => 0); for (const filter of parsePeq(text)) biquadResponse(filter, frequency_hz).forEach((v, i) => { level_db[i] += v; }); return { frequency_hz: [...frequency_hz], level_db }; }
function median(values: number[]): number { const sorted = [...values].sort((a, b) => a - b); const mid = Math.floor(sorted.length / 2); return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2; }

export function generateV030(base: Curve, inputs: V030Input[]): V030Result {
  assertCurve(base); if (!base.frequency_hz.some((f) => f === ANCHOR_HZ)) throw new Error("Base Target must contain exact 1000 Hz"); if (!inputs.length) throw new Error("at least one IEM is required");
  // Never extrapolate a measurement. A mounted deployment can contain an
  // older prepared file with a slightly shorter endpoint than the Base Target;
  // use the covered portion of the Base Target master grid in that case.
  const grid = base.frequency_hz.filter((f) => inputs.every((input) => f >= input.measurement.frequency_hz[0] && f <= input.measurement.frequency_hz[input.measurement.frequency_hz.length - 1]));
  if (!grid.some((f) => f === ANCHOR_HZ)) throw new Error("measurement curves must share the exact 1000 Hz anchor");
  const baseOnGrid = normalized({ frequency_hz: [...grid], level_db: interpolateLog(base, grid) }); const deltas: number[][] = []; const per_iem: V030Result["per_iem"] = {};
  for (const input of inputs) { const measurement = normalized({ frequency_hz: [...grid], level_db: interpolateLog(input.measurement, grid) }); const reconstructed = reconstructPeq(input.preferred, grid); const peq = normalized(reconstructed); const desired = { frequency_hz: [...grid], level_db: measurement.level_db.map((v, i) => v + peq.level_db[i]) }; const delta = { frequency_hz: [...grid], level_db: desired.level_db.map((v, i) => v - baseOnGrid.level_db[i]) }; deltas.push(delta.level_db); per_iem[input.id] = { normalized_measurement: measurement, reconstructed_peq: reconstructed, normalized_peq: peq, desired_response: desired, delta }; }
  const median_delta = { frequency_hz: [...grid], level_db: grid.map((_, i) => median(deltas.map((d) => d[i]))) }; const mad = { frequency_hz: [...grid], level_db: grid.map((_, i) => median(deltas.map((d) => Math.abs(d[i] - median_delta.level_db[i])))) }; const n_plus = grid.map((_, i) => deltas.filter((d) => d[i] > EPSILON_DB).length); const n_minus = grid.map((_, i) => deltas.filter((d) => d[i] < -EPSILON_DB).length); const n_zero = grid.map((_, i) => deltas.length - n_plus[i] - n_minus[i]);
  const final_target = { frequency_hz: [...grid], level_db: grid.map((f, i) => { const baseLevel = interpolateLog(base, [f])[0]; if (f < 1000 || f >= 12000) return baseLevel; if (f <= 11200) return baseLevel + median_delta.level_db[i]; const t = (f - 11200) / 800; const smooth = 1 - (3 * t * t - 2 * t * t * t); return baseLevel + median_delta.level_db[i] * smooth; }) };
  const warnings = ["v0.3.0 uses no default 8.1275 kHz safety notch.", "11.2–12 kHz taper uses cubic smoothstep pending confirmation of the original source artifact."]; if (grid.length !== base.frequency_hz.length) warnings.push("Master grid was clipped to the common covered range; no measurement extrapolation was applied.");
  return { normalized_base: baseOnGrid, per_iem, median_delta, mad, final_target, grid: { master_frequency_hz: [...base.frequency_hz], represented_frequency_hz: [...grid], clipped: grid.length !== base.frequency_hz.length }, diagnostics: { n_plus, n_minus, n_zero, warnings } };
}
