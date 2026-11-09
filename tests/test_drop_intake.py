"""Pure helper: dropped paths → AddPaths inputs + UNKNOWN skip feedback."""

from __future__ import annotations

from pathlib import Path

from paperflick.core.batch import DocKind
from paperflick.core.batch.drop_intake import classify_dropped_paths, parse_dnd_files_payload
from paperflick.core.batch.formats import kind_for_path


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x")
    return path


def test_parse_dnd_files_payload_braces_and_backslashes() -> None:
    spaced = r"C:\My Documents\a.pdf"
    plain = r"D:\projects\printer-advance-wt-28\.smoke_tmp\a.pdf"
    payload = "{" + spaced + "} " + plain
    assert parse_dnd_files_payload(payload) == [Path(spaced), Path(plain)]


def test_kind_for_path_by_suffix_only(tmp_path: Path) -> None:
    assert kind_for_path(tmp_path / "a.PDF") is DocKind.PDF
    assert kind_for_path(tmp_path / "b.PNG") is DocKind.IMAGE
    assert kind_for_path(tmp_path / "c.docx") is DocKind.DOCX
    assert kind_for_path(tmp_path / "d.txt") is DocKind.UNKNOWN
    assert kind_for_path(tmp_path / "noext") is DocKind.UNKNOWN


def test_classify_keeps_supported_skips_unknown(tmp_path: Path) -> None:
    pdf = _touch(tmp_path / "a.pdf")
    png = _touch(tmp_path / "b.png")
    txt = _touch(tmp_path / "c.txt")
    junk = _touch(tmp_path / "d.xyz")

    intake = classify_dropped_paths([pdf, txt, png, junk])

    assert intake.paths == (pdf, png)
    assert intake.skipped_unknown == 2
    assert intake.status_text == "已跳过 2 个不支持的文件"


def test_classify_expands_folder_and_filters(tmp_path: Path) -> None:
    folder = tmp_path / "bundle"
    good = _touch(folder / "ok.pdf")
    _touch(folder / "nested" / "bad.txt")
    _touch(folder / "pic.png")

    intake = classify_dropped_paths([folder])

    assert {path.name for path in intake.paths} == {"ok.pdf", "pic.png"}
    assert intake.skipped_unknown == 1
    assert intake.status_text == "已跳过 1 个不支持的文件"
    assert good in intake.paths


def test_classify_all_unsupported_adds_nothing(tmp_path: Path) -> None:
    first = _touch(tmp_path / "a.txt")
    second = _touch(tmp_path / "b.log")

    intake = classify_dropped_paths([first, second])

    assert intake.paths == ()
    assert intake.skipped_unknown == 2
    assert intake.status_text == "已跳过 2 个不支持的文件"


def test_classify_all_supported_has_empty_status(tmp_path: Path) -> None:
    pdf = _touch(tmp_path / "a.pdf")
    docx = _touch(tmp_path / "b.docx")

    intake = classify_dropped_paths([pdf, docx])

    assert intake.paths == (pdf, docx)
    assert intake.skipped_unknown == 0
    assert intake.status_text == ""


def test_classify_mixed_drop_keeps_good_only(tmp_path: Path) -> None:
    good = _touch(tmp_path / "good.pdf")
    folder = tmp_path / "more"
    _touch(folder / "also.png")
    _touch(folder / "skip.md")

    intake = classify_dropped_paths([good, folder, tmp_path / "gone.xyz"])

    names = [path.name for path in intake.paths]
    assert names == ["good.pdf", "also.png"]
    assert intake.skipped_unknown == 2
