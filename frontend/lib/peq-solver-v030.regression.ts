import { solvePeqV030, type PeqSolverConfig } from "./peq-solver-v030";
import type { Curve } from "./personal-earprint-v030";

/** Executable regression fixture for browser-console/CI harnesses. */
export function runPeqAntiOverfitRegression(): void {
  const frequency_hz = Array.from({ length: 97 }, (_, i) => 1000 * 2 ** (i / 24));
  const level_db = frequency_hz.map((frequency) => {
    const broad = 2.5 * Math.exp(-((Math.log2(frequency / 2500)) ** 2) / 1.8);
    const ripple = 1.8 * Math.sin(Math.log2(frequency / 1000) * Math.PI * 24) * (frequency > 5000 ? 1 : 0);
    return broad + ripple;
  });
  const config: PeqSolverConfig = {
    maxBands: 10,
    narrowQThreshold: 4,
    evidenceWindowOctaves: 1 / 6,
    minEvidenceDb: 1,
    minEvidenceSupport: 0.6,
    candidateQ: [1, 2, 4, 8],
    gainStepDb: 0.5,
    frequencyStepOctaves: 1 / 12,
    erbBandwidthOctaves: 1 / 3,
    weights: { pointwise: 1, erb: 1, slope: 0.5, curvature: 0.25, topology: 0.5, stability: 0.25 },
    improvementTolerance: 0.01,
    maxIterations: 100,
    quantization: { frequencyStepHz: 1, gainStepDb: 0.1, qStep: 0.01 },
  };
  const target: Curve = { frequency_hz, level_db };
  const first = solvePeqV030(target, config), second = solvePeqV030(target, config);
  if (first.filters.length > 10 || JSON.stringify(first.filters) !== JSON.stringify(second.filters)) throw new Error("solver is not capped/deterministic");
  if (first.filters.length >= 24) throw new Error("solver created a filter for every treble ripple");
  if (!first.response.level_db.every(Number.isFinite)) throw new Error("quantized response is not finite");
}
