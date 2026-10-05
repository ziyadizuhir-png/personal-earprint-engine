import numpy as np
from engine.v44_engine import Curve, IEMInput, PEQFilter, construct_target, generate, parse_peq, reconstruct_peq

def curve(f, y): return Curve(f.tolist(), y.tolist())

def fixture():
    f = np.array([20, 1000, 2000, 12000, 13000, 14000, 20000.], float)
    base = curve(f, np.array([1, 2, 3, 4, 5, 6, 7.]))
    iem = IEMInput("x", base, base, "Filter 1: ON PK Fc 2378 Hz Gain 0.6 dB Q 1.41")
    return f, base, iem

def test_parser_and_biquad_types():
    assert parse_peq("Filter 1: ON PK Fc 2378 Hz Gain 0.6 dB Q 1.41\nHS,100,2,0.7\nLS,60,-1,0.8") == [PEQFilter("PK",2378,0.6,1.41), PEQFilter("HS",100,2,0.7), PEQFilter("LS",60,-1,0.8)]
    f = np.array([1000., 2000.]); assert np.all(np.isfinite(reconstruct_peq(parse_peq("PK,1000,1,1"), f)))

def test_master_grid_anchor_statistics_and_pending_stages():
    f, base, iem = fixture(); result = generate(base, [iem])
    assert result.master_grid_hz == f.tolist()
    assert result.normalized_base_target.level_db[1] == 0
    assert result.mad.level_db == [0.0] * len(f)
    assert len(result.n_plus) == len(f) and len(result.n_minus) == len(f) and len(result.n_zero) == len(f)
    assert result.final_target is not None
    assert result.delta_safe is not None

def test_frequency_ownership_and_exact_linear_fade():
    f, base, _ = fixture(); delta = curve(f, np.full_like(f, 2.0)); out = construct_target(base, delta)
    assert out.level_db[0] == base.level_db[0]
    assert out.level_db[1] == base.level_db[1] + 2
    assert out.level_db[2] == base.level_db[2] + 2
    assert out.level_db[3] == base.level_db[3] + 2
    assert out.level_db[4] == base.level_db[4] + 1
    assert out.level_db[5] == base.level_db[5]
    assert out.level_db[6] == base.level_db[6]

def test_raw_input_unchanged_and_modes_are_exactly_two():
    f, base, iem = fixture(); before = list(iem.prepared_measurement.level_db)
    assert generate(base, [iem], "pure_earprint").mode == "pure_earprint"
    assert generate(base, [iem], "robust_target").mode == "robust_target"
    assert iem.prepared_measurement.level_db == before

def test_v44_inputs_require_exact_1000_hz_anchor():
    f = np.array([20., 900., 1100., 14000., 20000.])
    base = curve(f, np.zeros_like(f))
    iem = IEMInput("x", base, base, "PK,1000,0,1")
    try:
        generate(base, [iem])
    except ValueError as exc:
        assert "exact 1000 Hz" in str(exc)
    else:
        raise AssertionError("unprepared V4.4 input was accepted")
