import numpy as np

from engine.v44.v44 import Curve, IEMInput, generate, reconstruct_peq, parse_peq


def curve(values):
    return Curve([20.0, 1000.0, 11200.0, 11800.0, 12000.0, 20000.0], list(values))


def test_v030_biquad_reconstruction_is_continuous_at_48khz():
    response = reconstruct_peq(parse_peq("Filter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n"), np.array([20.0, 1000.0, 2000.0]), 48000.0)
    assert np.all(np.isfinite(response))
    assert response[1] > 2.9


def test_v030_has_no_default_8127_5_hz_notch_and_uses_11200_12000_taper():
    base = curve([0.0] * 6)
    iem = IEMInput("fixture", base, base, "Filter 1: ON PK Fc 6000 Hz Gain 2 dB Q 1\n")
    result = generate(base, [iem])
    final = np.asarray(result.final_target.level_db)
    median = np.asarray(result.median_delta.level_db)
    assert np.allclose(final[[0, 5]], 0.0)
    assert not np.isclose(final[2], 0.0)
    assert abs(final[3]) < abs(median[3])
    assert np.isclose(final[4], 0.0)


def test_v030_robust_center_is_pointwise_median_with_mad_diagnostics():
    base = curve([0.0] * 6)
    inputs = [IEMInput(str(i), curve([0.0, 0.0, float(i), float(i), 0.0, 0.0]), "Filter 1: ON PK Fc 1000 Hz Gain 0 dB Q 1\n") for i in [1, 2, 100]]
    result = generate(base, inputs)
    assert np.isclose(result.median_delta.level_db[2], 2.0, atol=1e-9)
    assert result.mad.level_db[2] > 0
