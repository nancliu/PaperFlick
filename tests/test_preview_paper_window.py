"""Headless MainWindow proof for Preview Paper overlay. Child process."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.gui
def test_headless_preview_paper_window(require_tk: None) -> None:
    """Radio Facing swaps paper aspect; PrinterDefault stays unforced; reopen matches."""
    script = (
        Path(__file__).resolve().parents[1]
        / ".cursor"
        / "skills"
        / "verify-paperflick"
        / "_run_preview_paper.py"
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
    assert "PASS preview-paper" in completed.stdout
