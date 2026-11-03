"""Human readable byte sizes using binary MiB/KiB units."""


def format_file_size(size: int) -> str:
    if type(size) is not int or size < 0:
        raise ValueError("File size must be a nonnegative byte count")
    if size < 1024:
        return f"{size} B"
    if size < 1024**2:
        return f"{size / 1024:.1f} KiB"
    if size < 1024**3:
        return f"{size / 1024**2:.2f} MiB"
    return f"{size / 1024**3:.2f} GiB"
