"""The font installer is verifiable without downloading a font in CI."""
from __future__ import annotations
import io
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from install_fonts import FONT_SHA, LICENSE_SHA, git_blob_sha, install_one, validate_content


class FakeResponse:
    def __init__(self, content):
        self._stream = io.BytesIO(content)

    def __enter__(self): return self
    def __exit__(self, *_): self._stream.close()
    def read(self, n): return self._stream.read(n)


def test_git_blob_verification():
    data = b"hello font"
    sha = git_blob_sha(data)
    assert len(sha) == 40
    assert validate_content(data, sha)
    assert not validate_content(data + b"x", sha)


def test_installer_valid_data(tmp_path):
    text = b"license placeholder for unit test"
    result = install_one("OFL.txt", git_blob_sha(text), tmp_path,
                         opener=lambda request, timeout: FakeResponse(text))
    assert result == "installed"
    assert (tmp_path / "OFL.txt").read_bytes() == text
    assert install_one("OFL.txt", git_blob_sha(text), tmp_path,
                       opener=lambda request, timeout: pytest.fail("Downloaded twice")) == "verified existing"


def test_installer_rejects_invalid_data(tmp_path):
    with pytest.raises(ValueError, match="checksum"):
        install_one("OFL.txt", LICENSE_SHA, tmp_path,
                    opener=lambda request, timeout: FakeResponse(b"bad bytes"))
    assert not (tmp_path / "OFL.txt").exists()


def test_manifest_contains_all_pinned_weights():
    assert set(FONT_SHA) == {
        "ZenMaruGothic-Regular.ttf",
        "ZenMaruGothic-Medium.ttf",
        "ZenMaruGothic-Bold.ttf",
    }
    assert all(len(v) == 40 for v in FONT_SHA.values())
