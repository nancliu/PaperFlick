"""Headless MainWindow proof for folded settings, 演练, and About."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.gui
def test_headless_settings_about_window(require_tk: None) -> None:
    """设置 stays collapsed, Dry Run copy is 演练, and the version badge opens About."""
    script = (
        Path(__file__).resolve().parents[1]
        / ".cursor"
        / "skills"
        / "verify-paperflick"
        / "_run_settings_about.py"
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
    assert "PASS settings-about" in completed.stdout
