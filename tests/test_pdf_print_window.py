"""Headless MainWindow proof for PDF print. Runs in a child process."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.gui
def test_headless_pdf_print_window(require_tk: None) -> None:
    """Dry Run off records Sumatra arguments and keeps the Batch moving."""
    script = (
        Path(__file__).resolve().parents[1]
        / ".cursor"
        / "skills"
        / "verify-paperflick"
        / "_run_pdf_print.py"
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
    assert "PASS pdf-real-print" in completed.stdout
