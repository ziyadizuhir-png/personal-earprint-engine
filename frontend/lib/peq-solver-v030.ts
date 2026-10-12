import type { Curve, PeqFilter } from "./personal-earprint-v030";

export type SolverFilter = PeqFilter;

/**
 * v0.3.0 specifies the browser solver location and the 48 kHz PEQ model, but
 * does not specify PEQ fitting thresholds. These values are therefore
 * configuration, not canonical target math. Keep them visible to callers.
 */
export type PeqSolverConfig = {
  maxBands: 10;
  narrowQThreshold: number;
  evidenceWindowOctaves: number;
  minEvidenceDb: number;
  minEvidenceSupport: number;
  candidateQ: number[];
  gainStepDb: number;
  frequencyStepOctaves: number;
  erbBandwidthOctaves: number;
  weights: { pointwise: number; erb: number; slope: number; curvature: number; topology: number; stability: number };
  improvementTolerance: number;
  maxIterations: number;
  quantization: { frequencyStepHz: number; gainStepDb: number; qStep: number };
};

export const SPEC_BLOCKED_SOLVER_DEFAULTS = {
  narrowQThreshold: 4,
  evidenceWindowOctaves: 1 / 6,
  minEvidenceDb: 1,
  minEvidenceSupport: 0.6,
  candidateQ: [0.7, 1, 1.4, 2, 3, 4, 6, 8],
  gainStepDb: 0.5,
  frequencyStepOctaves: 1 / 12,
  erbBandwidthOctaves: 1 / 3,
  weights: { pointwise: 1, erb: 1, slope: 0.5, curvature: 0.25, topology: 0.5, stability: 0.25 },
  improvementTolerance: 0.01,
  maxIterations: 100,
  quantization: { frequencyStepHz: 1, gainStepDb: 0.1, qStep: 0.01 },
} as const;

export type SolverDiagnostics = {
  stopReason: "no_improving_candidate" | "max_bands" | "max_iterations";
  objective: number;
  bandsConsidered: number;
  specBlocked: string[];
};

export type PeqSolverResult = { filters: SolverFilter[]; response: Curve; diagnostics: SolverDiagnostics };

type Objective = { total: number; pointwise: number; erb: number; slope: number; curvature: number; topology: number; stability: number };
type Candidate = SolverFilter & { narrow: boolean };

function assertCurve(c: Curve): void {
  if (c.frequency_hz.length !== c.level_db.length || c.frequency_hz.length < 3) throw new Error("curve arrays must match and contain at least three points");
  for (let i = 0; i < c.frequency_hz.length; i++) if (!Number.isFinite(c.frequency_hz[i]) || !Number.isFinite(c.level_db[i]) || c.frequency_hz[i] <= 0 || (i > 0 && c.frequency_hz[i] <= c.frequency_hz[i - 1])) throw new Error("curve must be finite and strictly ascending");
}

function mean(values: number[]): number { return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0; }
function absMean(values: number[]): number { return mean(values.map(Math.abs)); }
function logDistance(a: number, b: number): number { return Math.log2(a / b); }
function quantize(value: number, step: number): number { return Math.round(value / step) * step; }

function biquadResponse(filter: SolverFilter, frequency_hz: number[]): number[] {
  const A = 10 ** (filter.gain_db / 40), w0 = 2 * Math.PI * filter.frequency_hz / 48000, alpha = Math.sin(w0) / (2 * filter.q), c = Math.cos(w0);
  const b0 = 1 + alpha * A, b1 = -2 * c, b2 = 1 - alpha * A, a0 = 1 + alpha / A, a1 = -2 * c, a2 = 1 - alpha / A;
  return frequency_hz.map((f) => { const z = { re: Math.cos(-2 * Math.PI * f / 48000), im: Math.sin(-2 * Math.PI * f / 48000) }; const z2 = { re: z.re * z.re - z.im * z.im, im: 2 * z.re * z.im }; const nr = b0 + b1 * z.re + b2 * z2.re, ni = b1 * z.im + b2 * z2.im, dr = a0 + a1 * z.re + a2 * z2.re, di = a1 * z.im + a2 * z2.im; return 20 * Math.log10(Math.max(Math.hypot(nr, ni) / Math.hypot(dr, di), 1e-300)); });
}

function responseFor(filters: SolverFilter[], frequency_hz: number[]): number[] {
  const response = frequency_hz.map(() => 0);
  for (const filter of filters) biquadResponse(filter, frequency_hz).forEach((value, index) => { response[index] += value; });
  return response;
}

function derivatives(values: number[], frequencies: number[]): { slope: number[]; curvature: number[] } {
  const x = frequencies.map((f) => Math.log2(f));
  const slope = values.map((_, i) => i === 0 ? (values[1] - values[0]) / (x[1] - x[0]) : i === values.length - 1 ? (values[i] - values[i - 1]) / (x[i] - x[i - 1]) : (values[i + 1] - values[i - 1]) / (x[i + 1] - x[i - 1]));
  const curvature = values.map((_, i) => i === 0 || i === values.length - 1 ? 0 : slope[i + 1] - slope[i - 1]);
  return { slope, curvature };
}

function objective(target: Curve, response: number[], filters: SolverFilter[], config: PeqSolverConfig): Objective {
  const residual = target.level_db.map((value, i) => response[i] - value);
  const targetD = derivatives(target.level_db, target.frequency_hz), responseD = derivatives(response, target.frequency_hz);
  const bins = new Map<number, number[]>();
  target.frequency_hz.forEach((frequency, i) => { const center = Math.round(Math.log2(frequency / 1000) / config.erbBandwidthOctaves); const values = bins.get(center) || []; values.push(i); bins.set(center, values); });
  const erb = [...bins.values()].map((indices) => mean(indices.map((i) => residual[i])));
  const targetErb = [...bins.values()].map((indices) => mean(indices.map((i) => target.level_db[i])));
  const responseErb = [...bins.values()].map((indices) => mean(indices.map((i) => response[i])));
  const targetTransitions = targetD.slope.slice(1).map((v, i) => Math.sign(v) !== Math.sign(targetD.slope[i]) ? 1 : 0);
  const responseTransitions = responseD.slope.slice(1).map((v, i) => Math.sign(v) !== Math.sign(responseD.slope[i]) ? 1 : 0);
  const stability = filters.reduce((sum, filter) => sum + Math.max(0, filter.q - config.narrowQThreshold) ** 2 + Math.abs(filter.gain_db) * Math.max(0, filter.q - config.narrowQThreshold), 0);
  const parts = { pointwise: absMean(residual), erb: absMean(responseErb.map((v, i) => v - targetErb[i])), slope: absMean(responseD.slope.map((v, i) => v - targetD.slope[i])), curvature: absMean(responseD.curvature.map((v, i) => v - targetD.curvature[i])), topology: absMean(responseTransitions.map((v, i) => v - targetTransitions[i])), stability };
  return { ...parts, total: parts.pointwise * config.weights.pointwise + parts.erb * config.weights.erb + parts.slope * config.weights.slope + parts.curvature * config.weights.curvature + parts.topology * config.weights.topology + parts.stability * config.weights.stability };
}

function hasEvidence(target: Curve, residual: number[], index: number, candidate: Candidate, config: PeqSolverConfig): boolean {
  if (!candidate.narrow) return true;
  const sign = Math.sign(residual[index]); if (!sign || Math.abs(residual[index]) < config.minEvidenceDb) return false;
  const nearby = residual.filter((_, i) => Math.abs(logDistance(target.frequency_hz[i], candidate.frequency_hz)) <= config.evidenceWindowOctaves);
  return nearby.length > 0 && nearby.filter((value) => Math.sign(value) === sign && Math.abs(value) >= config.minEvidenceDb).length / nearby.length >= config.minEvidenceSupport;
}

function quantized(filter: SolverFilter, config: PeqSolverConfig): SolverFilter { return { kind: "PK", frequency_hz: quantize(filter.frequency_hz, config.quantization.frequencyStepHz), gain_db: quantize(filter.gain_db, config.quantization.gainStepDb), q: quantize(filter.q, config.quantization.qStep) }; }

export function solvePeqV030(target: Curve, config: PeqSolverConfig): PeqSolverResult {
  assertCurve(target); if (config.maxBands !== 10) throw new Error("v0.3.0 solver band cap is canonically 10");
  if (!config.candidateQ.length || config.weights.pointwise < 0 || config.weights.erb < 0) throw new Error("invalid PEQ solver configuration");
  const filters: SolverFilter[] = [], frequency_hz = [...target.frequency_hz]; let response = responseFor(filters, frequency_hz); let best = objective(target, response, filters, config); let iterations = 0, considered = 0;
  let stopReason: SolverDiagnostics["stopReason"] = "max_bands";
  while (filters.length < config.maxBands && iterations++ < config.maxIterations) {
    const residual = target.level_db.map((value, i) => value - response[i]); const candidates: Candidate[] = [];
    for (let i = 0; i < frequency_hz.length; i++) for (const q of config.candidateQ) { const gain = quantize(residual[i], config.gainStepDb); if (!gain) continue; const candidate = { kind: "PK" as const, frequency_hz: frequency_hz[i], gain_db: gain, q, narrow: q >= config.narrowQThreshold }; if (hasEvidence(target, residual, i, candidate, config)) candidates.push(candidate); }
    candidates.sort((a, b) => a.frequency_hz - b.frequency_hz || a.q - b.q || a.gain_db - b.gain_db); let accepted: { filter: SolverFilter; response: number[]; score: Objective } | undefined;
    for (const candidate of candidates) { considered++; const filter = quantized(candidate, config); if (!filter.gain_db || filters.some((item) => item.frequency_hz === filter.frequency_hz && item.q === filter.q)) continue; const nextFilters = [...filters, filter]; const nextResponse = responseFor(nextFilters, frequency_hz); const score = objective(target, nextResponse, nextFilters, config); if (best.total - score.total > config.improvementTolerance && (!accepted || score.total < accepted.score.total)) accepted = { filter, response: nextResponse, score }; }
    if (!accepted) { stopReason = filters.length >= config.maxBands ? "max_bands" : "no_improving_candidate"; break; }
    filters.push(accepted.filter); response = accepted.response; best = accepted.score;
  }
  if (iterations >= config.maxIterations && filters.length < config.maxBands) stopReason = "max_iterations";
  return { filters, response: { frequency_hz, level_db: response }, diagnostics: { stopReason, objective: best.total, bandsConsidered: considered, specBlocked: ["narrow-feature thresholds", "objective weights", "quantization increments", "candidate Q set", "early-stop tolerance"] } };
}
