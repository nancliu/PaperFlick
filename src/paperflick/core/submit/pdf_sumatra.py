"""PDF Print Jobs via a SumatraPDF silent-print command."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from paperflick.core.batch.formats import DocKind
from paperflick.core.batch.types import Facing, resolve_facing
from paperflick.core.submit.port import (
    REASON_UNSUPPORTED,
    SubmitFailed,
    SubmitOk,
    SubmitRequest,
    SubmitResult,
)
from paperflick.core.submit.preflight import preflight

REASON_SUMATRA_MISSING = "未找到 SumatraPDF"
REASON_SUMATRA_FAILED = "SumatraPDF 打印失败"
REASON_SUMATRA_TIMEOUT = "SumatraPDF 打印超时"
REASON_SUMATRA_LAUNCH = "无法启动 SumatraPDF"

SUMATRA_TIMEOUT_SECONDS = 120
_ENV_SUMATRA = "PAPERFLICK_SUMATRA"
_DETAIL_LIMIT = 120

SumatraRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
Which = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class SumatraJob:
    """One silent PDF print.

    ``facing`` None leaves the direction to the printer. ``printer`` None, or a
    blank name, prints to the Windows default printer.
    """

    executable: Path
    document: Path
    printer: str | None
    facing: Facing | None


def sumatra_argv(job: SumatraJob) -> list[str]:
    """Return the SumatraPDF argument vector for one silent print.

    ``portrait`` and ``landscape`` are Sumatra print-settings tokens. Omitting
    both leaves the printer's current default direction unchanged.
    """
    argv = [str(job.executable)]
    printer = job.printer.strip() if job.printer else ""
    if printer:
        argv.extend(["-print-to", printer])
    else:
        argv.append("-print-to-default")
    setting = _facing_token(job.facing)
    if setting is not None:
        argv.extend(["-print-settings", setting])
    argv.append("-silent")
    argv.append(str(job.document))
    return argv


def _facing_token(facing: Facing | None) -> str | None:
    """Map a resolved direction to Sumatra's token. None means do not force one."""
    if facing is Facing.LANDSCAPE:
        return "landscape"
    if facing is Facing.PORTRAIT:
        return "portrait"
    return None


def find_sumatra(
    *,
    environ: Mapping[str, str] | None = None,
    candidates: Sequence[Path] | None = None,
    which: Which | None = None,
) -> Path | None:
    """Return a SumatraPDF executable, or None when none can be used.

    ``PAPERFLICK_SUMATRA`` wins. A set value that is not a file returns None
    and does not fall through to another install.
    """
    env = os.environ if environ is None else environ
    override = env.get(_ENV_SUMATRA)
    if override is not None:
        path = Path(override)
        return path if path.is_file() else None

    search = _install_candidates(env) if candidates is None else candidates
    for path in search:
        if path.is_file():
            return path

    lookup = shutil.which if which is None else which
    for name in ("SumatraPDF", "SumatraPDF.exe"):
        found = lookup(name)
        if found is None:
            continue
        path = Path(found)
        if path.is_file():
            return path
    return None


def _install_candidates(environ: Mapping[str, str]) -> tuple[Path, ...]:
    """Well-known per-user and Program Files locations."""
    roots = (
        environ.get("LOCALAPPDATA"),
        environ.get("PROGRAMFILES"),
        environ.get("PROGRAMFILES(X86)"),
    )
    return tuple(Path(root) / "SumatraPDF" / "SumatraPDF.exe" for root in roots if root)


def run_sumatra_process(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Spawn one Sumatra command and wait until it exits.

    ``TimeoutExpired`` and ``OSError`` propagate. The submit port turns them
    into a Print Item failure.
    """
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=SUMATRA_TIMEOUT_SECONDS,
        check=False,
        creationflags=flags,
    )


class PdfSumatraSubmit:
    """Submit a PDF Print Item with SumatraPDF. Any other kind fails the item."""

    def __init__(self, executable: Path | None, *, run: SumatraRunner | None = None) -> None:
        self._executable = executable
        self._run = run_sumatra_process if run is None else run

    def submit(self, request: SubmitRequest) -> SubmitResult:
        """Preflight, then one silent print. A missing engine fails this item only."""
        failed = preflight(request)
        if failed is not None:
            return failed
        if request.item.kind is not DocKind.PDF:
            return SubmitFailed(REASON_UNSUPPORTED)
        executable = self._executable
        if executable is None or not executable.is_file():
            return SubmitFailed(REASON_SUMATRA_MISSING)
        job = SumatraJob(
            executable=executable,
            document=request.item.path,
            printer=request.printer,
            facing=resolve_facing(request.item.orientation, request.item.shape),
        )
        try:
            completed = self._run(sumatra_argv(job))
        except subprocess.TimeoutExpired:
            return SubmitFailed(REASON_SUMATRA_TIMEOUT)
        except OSError as exc:
            return _launch_failure(exc)
        return _from_run(completed)


def _from_run(completed: subprocess.CompletedProcess[str]) -> SubmitResult:
    """Map a finished process onto SubmitOk or SubmitFailed."""
    if completed.returncode == 0:
        return SubmitOk()
    detail = _clip(completed.stderr) or _clip(completed.stdout)
    if detail:
        return SubmitFailed(f"{REASON_SUMATRA_FAILED}：{detail}")
    return SubmitFailed(REASON_SUMATRA_FAILED)


def _clip(text: str | bytes | None) -> str:
    """Collapse whitespace and cap the length shown on a list row."""
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    return " ".join(text.split())[:_DETAIL_LIMIT]


def _launch_failure(exc: OSError) -> SubmitFailed:
    """Turn a spawn error into a row reason."""
    detail = _clip(exc.strerror or str(exc))
    if detail:
        return SubmitFailed(f"{REASON_SUMATRA_LAUNCH}：{detail}")
    return SubmitFailed(REASON_SUMATRA_LAUNCH)
