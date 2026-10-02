from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import latencylab
from latencylab.version import FALLBACK_VERSION, VERSION_FILE, read_version

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_version_file_is_the_only_declared_version() -> None:
    import latencylab_ui

    recorded = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    assert recorded
    assert VERSION_FILE == REPO_ROOT / "VERSION"
    assert latencylab.__version__ == recorded
    assert latencylab_ui.__version__ == recorded


def test_read_version_falls_back_when_the_file_is_absent(tmp_path: Path) -> None:
    assert read_version(tmp_path / "VERSION") == FALLBACK_VERSION


def test_read_version_falls_back_when_the_file_is_empty(tmp_path: Path) -> None:
    empty = tmp_path / "VERSION"
    empty.write_text("   \n", encoding="utf-8")

    assert read_version(empty) == FALLBACK_VERSION


def _site(tmp_path: Path, body: str) -> Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "index.html").write_text(body, encoding="utf-8")
    return docs


def test_target_files_collects_html_and_markdown_only(tmp_path: Path) -> None:
    import stamp_version

    docs = _site(tmp_path, "<p>v<!--VERSION-->0.0.0<!--/VERSION--></p>")
    (docs / "notes.md").write_text("# notes", encoding="utf-8")
    (docs / "styles.css").write_text("body{}", encoding="utf-8")

    names = [path.name for path in stamp_version.target_files(docs)]

    assert names == ["index.html", "notes.md"]


def test_stamp_file_rewrites_the_token(tmp_path: Path) -> None:
    import stamp_version

    docs = _site(tmp_path, "<p>v<!--VERSION-->0.0.0<!--/VERSION--></p>")
    page = docs / "index.html"

    assert stamp_version.stamp_file(page, "9.9.9") is True
    assert page.read_text(encoding="utf-8") == (
        "<p>v<!--VERSION-->9.9.9<!--/VERSION--></p>"
    )


def test_stamp_file_leaves_an_already_current_file_alone(tmp_path: Path) -> None:
    import stamp_version

    docs = _site(tmp_path, "<p>v<!--VERSION-->9.9.9<!--/VERSION--></p>")

    assert stamp_version.stamp_file(docs / "index.html", "9.9.9") is False


def test_main_stamps_then_becomes_a_no_op(tmp_path: Path, capsys) -> None:
    import stamp_version

    docs = _site(tmp_path, "<p>v<!--VERSION-->0.0.0<!--/VERSION--></p>")

    assert stamp_version.main(docs, "9.9.9") == 0
    first = capsys.readouterr().out
    assert "VERSION = 9.9.9" in first
    assert "Stamped docs/index.html" in first.replace("\\", "/")

    assert stamp_version.main(docs, "9.9.9") == 0
    assert "No files needed stamping." in capsys.readouterr().out


def test_main_defaults_to_the_version_file(tmp_path: Path, capsys) -> None:
    import stamp_version

    docs = _site(tmp_path, "<p>no token here</p>")

    assert stamp_version.main(docs) == 0
    assert f"VERSION = {latencylab.__version__}" in capsys.readouterr().out


def _linked_site(tmp_path: Path, css: bytes) -> Path:
    docs = _site(
        tmp_path,
        '<link rel="stylesheet" href="styles.css?v=stale">'
        '<link href="https://example.com/x.css"><script src="/root.js"></script>',
    )
    (docs / "styles.css").write_bytes(css)
    return docs


def test_version_assets_stamps_the_content_hash(tmp_path: Path) -> None:
    import stamp_version

    docs = _linked_site(tmp_path, b"body{}\n")
    page = docs / "index.html"
    digest = hashlib.sha256(b"body{}\n").hexdigest()
    expected = digest[: stamp_version.ASSET_HASH_LENGTH]

    assert stamp_version.version_assets(page) is True
    assert page.read_text(encoding="utf-8") == (
        f'<link rel="stylesheet" href="styles.css?v={expected}">'
        '<link href="https://example.com/x.css"><script src="/root.js"></script>'
    )


def test_version_assets_is_idempotent(tmp_path: Path) -> None:
    import stamp_version

    page = _linked_site(tmp_path, b"body{}\n") / "index.html"
    stamp_version.version_assets(page)
    first = page.read_bytes()

    assert stamp_version.version_assets(page) is False
    assert page.read_bytes() == first


def test_main_versions_asset_links_then_becomes_a_no_op(tmp_path: Path, capsys) -> None:
    import stamp_version

    docs = _linked_site(tmp_path, b"body{}\n")

    assert stamp_version.main(docs, "9.9.9") == 0
    first = capsys.readouterr().out
    assert "Versioned assets in docs/index.html" in first.replace("\\", "/")

    assert stamp_version.main(docs, "9.9.9") == 0
    assert "No asset links needed versioning." in capsys.readouterr().out


def test_asset_hash_changes_when_the_file_changes(tmp_path: Path) -> None:
    import stamp_version

    css = tmp_path / "styles.css"
    css.write_bytes(b"body{}\n")
    before = stamp_version.asset_hash(css)
    css.write_bytes(b"body{color:red}\n")

    assert stamp_version.asset_hash(css) != before


def test_asset_hash_ignores_crlf_versus_lf(tmp_path: Path) -> None:
    import stamp_version

    lf = tmp_path / "lf.css"
    crlf = tmp_path / "crlf.css"
    lf.write_bytes(b"a{}\nb{}\n")
    crlf.write_bytes(b"a{}\r\nb{}\r\n")

    assert stamp_version.asset_hash(lf) == stamp_version.asset_hash(crlf)


def test_version_assets_keeps_the_page_line_endings(tmp_path: Path) -> None:
    import stamp_version

    docs = _site(tmp_path, "")
    page = docs / "index.html"
    page.write_bytes(b'<p>a</p>\r\n<link href="styles.css">\r\n')
    (docs / "styles.css").write_bytes(b"body{}\n")

    assert stamp_version.version_assets(page) is True
    assert page.read_bytes().count(b"\r\n") == 2


def test_version_assets_refuses_a_missing_asset(tmp_path: Path) -> None:
    import stamp_version

    page = _site(tmp_path, '<link href="gone.css">') / "index.html"

    with pytest.raises(FileNotFoundError, match="gone.css"):
        stamp_version.version_assets(page)
