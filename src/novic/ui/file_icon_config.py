"""Central place to declare file icon mappings.

Edit this file to add or change icons without touching the MainWindow code.

How to add icons:
    1. Drop your icon image (png / svg) into:  src/novic/resources/icons/files/
    2. Add a line in ICONS_BY_EXTENSION or ICONS_BY_FILENAME below.
    3. (Optional) Change DEFAULT_FILE_ICON if you want a different generic file icon.

Supported keys:
    - Extensions: without leading dot (e.g. "py", "json", "md")
    - Filenames: exact match (case-insensitive) like "README.md" or ".gitignore"
"""
from __future__ import annotations
from pathlib import Path
from .file_icons import file_icon_registry

# Base directory where file icons live
_FILES_DIR = Path(__file__).resolve().parent.parent / "resources" / "icons" / "files"

# Default (generic) file icon (can be None to disable)
DEFAULT_FILE_ICON = _FILES_DIR / "regular_file.png"

# Map extensions -> icon path
ICONS_BY_EXTENSION = {
    "py": _FILES_DIR / "python_file.png",
    # "json": _FILES_DIR / "json_file.svg",
    # "md": _FILES_DIR / "markdown_file.svg",
}

# Groups of extensions that share the same icon (saves repetition)
GROUPED_EXTENSION_ICONS = {
    # Image formats
    "image_file.png": [
        "png", "jpg", "jpeg", "jpe", "jfif", "pjpeg", "pjp",
        "gif", "bmp", "dib", "tif", "tiff", "webp", "avif",
        "svg", "svgz", "ico", "heic", "heif" , "raw", "arw",
    ],
}

# Map exact filenames -> icon path
ICONS_BY_FILENAME = {
    # "README.md": _FILES_DIR / "readme_file.svg",
}

def apply_file_icon_config():
    """Register all configured icons into the shared registry."""
    if DEFAULT_FILE_ICON and DEFAULT_FILE_ICON.exists():
        file_icon_registry.set_default_file(str(DEFAULT_FILE_ICON))
    # Direct one-off mappings
    for ext, path in ICONS_BY_EXTENSION.items():
        if Path(path).exists():
            file_icon_registry.register_extension(ext, str(path))
    # Grouped mappings
    for icon_filename, extensions in GROUPED_EXTENSION_ICONS.items():
        icon_path = _FILES_DIR / icon_filename
        if not icon_path.exists():
            continue
        for ext in extensions:
            file_icon_registry.register_extension(ext, str(icon_path))
    for name, path in ICONS_BY_FILENAME.items():
        if Path(path).exists():
            file_icon_registry.register_filename(name, str(path))
    return file_icon_registry
