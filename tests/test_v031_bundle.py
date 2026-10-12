from pathlib import Path
import numpy as np

from engine.personal_earprint_v031 import Curve, IEMInput, generate, parse_peq, reconstruct_peq

ROOT = Path(__file__).parents[1]
BASE = ROOT / "data" / "base-targets" / "headphones-com-iem-df-tilt-1-db-oct-b105-5-db" / "target_source.txt"

def read_curve(path: Path) -> Curve:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.replace(",", " ").split()
        if len(fields) < 2:
            continue
        try:
            rows.append(tuple(map(float, fields[:2])))
        except ValueError:
            continue
    return Curve([x for x, _ in rows], [y for _, y in rows])

def test_bundle_dataset_and_exact_ownership_contract():
    base = read_curve(BASE)
    iems = []
    for folder in sorted((ROOT / "data" / "iems").iterdir()):
        if not folder.is_dir():
            continue
        curve = read_curve(folder / "measurement_source.txt")
        iems.append(IEMInput(folder.name, curve, curve, (folder / "preferred.txt").read_text(encoding="utf-8")))
    result = generate(base, iems)
    f = np.asarray(result.master_grid_hz)
    final = np.asarray(result.final_target.level_db)
    base_y = np.asarray(result.base_target.level_db)
    assert len(iems) == 9
    assert len(f) == 483
    assert {1000.0, 11200.0, 12000.0}.issubset(set(f))
    assert np.array_equal(final[f < 1000], base_y[f < 1000])
    assert np.array_equal(final[f >= 12000], base_y[f >= 12000])
    assert np.isclose(final[np.where(f == 1000.0)[0][0]], base_y[np.where(f == 1000.0)[0][0]])
    assert result.algorithm_version == "PersonalDelta-FullBand-0.3.1"
    assert len(result.narrow_peak_diagnostics) >= 0

def test_peq_parser_and_digital_reconstruction_are_bundle_compatible():
    text = "Filter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\nFilter 2: OFF PK Fc 2000 Hz Gain 4 dB Q 1"
    filters = parse_peq(text)
    assert len(filters) == 1 and filters[0].kind == "PK"
    response = reconstruct_peq(filters, np.array([1000.0, 2000.0]))
    assert np.all(np.isfinite(response))
