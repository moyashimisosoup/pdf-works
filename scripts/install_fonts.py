"""Fetch pinned, OFL-licensed Zen Maru Gothic for local/offline Qt use.

Run once from the source checkout:
    python scripts/install_fonts.py

No font binaries are committed to the repository. The bundled OFL notice is
downloaded from the same pinned upstream revision and verified as well.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

UPSTREAM_COMMIT = "553c872b216d1290e2902a466edcdc9682f0df6a"
BASE_URL = (
    "https://raw.githubusercontent.com/googlefonts/zen-marugothic/"
    + UPSTREAM_COMMIT + "/"
)
FONT_SHA = {
    "ZenMaruGothic-Regular.ttf": "c622402a1acf00c3481334de56439b3703cdcbb6",
    "ZenMaruGothic-Medium.ttf": "25ff26c6fc549e2dfe57d7e92524a5c1158720e6",
    "ZenMaruGothic-Bold.ttf": "aeaf890a35366fc7d08781886d2a04b85b5bec8c",
}
LICENSE_SHA = "7dc44f8017161dc4e1346b24cfd6e195c402633a"
FONT_DIR = Path(__file__).resolve().parents[1] / "src" / "pdf_works" / "resources" / "fonts"
MAX_DOWNLOAD = 5_000_000


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def validate_content(content: bytes, expected_sha: str) -> bool:
    return git_blob_sha(content) == expected_sha


def install_one(name: str, expected_sha: str, directory: Path = FONT_DIR,
                opener=urlopen) -> str:
    if name not in FONT_SHA and name != "OFL.txt":
        raise ValueError("Unrecognized upstream font file")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    if path.is_file() and validate_content(path.read_bytes(), expected_sha):
        return "verified existing"
    upstream_path = name if name == "OFL.txt" else "fonts/ttf/" + name
    request = Request(BASE_URL + upstream_path, headers={"User-Agent": "pdf-works-font-setup"})
    with opener(request, timeout=35) as response:
        content = response.read(MAX_DOWNLOAD + 1)
    if len(content) > MAX_DOWNLOAD or not validate_content(content, expected_sha):
        raise ValueError(f"Upstream size/checksum mismatch: {name}")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".font-", delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return "installed"


def main() -> int:
    items = {"OFL.txt": LICENSE_SHA, **FONT_SHA}
    try:
        # The license must accompany the font, including later EXE bundles.
        for name, sha in items.items():
            result = install_one(name, sha)
            print(f"{name}: {result}")
    except (OSError, ValueError) as exc:
        print(f"[ERROR] Font setup failed: {exc}")
        print("The app can still run with Windows fallback fonts.")
        return 1
    print("Zen Maru Gothic is ready for offline use. Restart pdf-works.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
