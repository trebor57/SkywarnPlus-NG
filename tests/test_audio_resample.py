"""Audio resampling without scipy."""

import numpy as np

from skywarnplus_ng.audio.audio_utils import _resample_audio_array


def test_resample_mono_halves_length_when_halving_rate():
    x = np.sin(np.linspace(0, 1, 8000, dtype=np.float32))
    y = _resample_audio_array(x, 8000, 4000)
    assert y.dtype == np.float32
    assert len(y) == 4000


def test_resample_noop_same_rate():
    x = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    y = _resample_audio_array(x, 8000, 8000)
    assert np.allclose(y, x)
