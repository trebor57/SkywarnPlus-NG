"""Tests for Piper model directory listing used by the config API."""

from pathlib import Path

from skywarnplus_ng.web.handlers.api_config import _list_piper_onnx_models


def test_list_piper_onnx_models_sorted_and_non_recursive(tmp_path: Path) -> None:
    piper = tmp_path / "piper"
    piper.mkdir()
    (piper / "b_voice.onnx").write_text("x")
    (piper / "a_voice.onnx").write_text("x")
    (piper / "readme.txt").write_text("n")
    sub = piper / "nested"
    sub.mkdir()
    (sub / "ignore.onnx").write_text("x")

    paths = _list_piper_onnx_models(piper)
    names = [Path(p).name for p in paths]
    assert names == ["a_voice.onnx", "b_voice.onnx"]
    assert all(Path(p).is_absolute() for p in paths)


def test_list_piper_onnx_models_missing_dir(tmp_path: Path) -> None:
    assert _list_piper_onnx_models(tmp_path / "nope") == []
