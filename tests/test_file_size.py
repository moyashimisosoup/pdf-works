from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pdf_works.core.file_size import format_file_size


@pytest.mark.parametrize("value,expected", [
    (0,"0 B"), (1023,"1023 B"), (1024,"1.0 KiB"),
    (1024*1024,"1.00 MiB"), (5*1024**3,"5.00 GiB"),
])
def test_display_size(value, expected):
    assert format_file_size(value) == expected


@pytest.mark.parametrize("value", [True, -1, -128, 2.5, "100"])
def test_invalid_sizes(value):
    with pytest.raises(ValueError):
        format_file_size(value)
