"""Headless MainWindow proof for list preview and inline remove. Child process."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.gui
def test_headless_list_preview_window(require_tk: None) -> None:
    """Row click opens one preview before raster; 移除 and 移除全部失败 behave."""
    script = (
        Path(__file__).resolve().parents[1]
        / ".cursor"
        / "skills"
        / "verify-paperflick"
        / "_run_list_preview.py"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    completed = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
        env=env,
    )
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert "PASS list-preview" in completed.stdout
