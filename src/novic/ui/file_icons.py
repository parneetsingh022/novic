from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileIconProvider

"""File icon configuration and lookup.

Usage:
    from .file_icons import file_icon_registry, FileIconProvider
    # Register custom icons early (e.g., before building the tree):
    file_icon_registry.register_extension("py", "resources/icons/files/python.svg")
    file_icon_registry.register_filename("README.md", "resources/icons/files/readme.svg")
    # Assign to QFileSystemModel:
    provider = FileIconProvider(file_icon_registry)
    model.setIconProvider(provider)

Icons are resolved in this order:
    1. Exact filename match
    2. Extension match (without leading dot)
    3. Default file icon (if set)
Otherwise returns an empty QIcon() allowing caller stylesheet / fallback.
"""

@dataclass(frozen=True)
class IconEntry:
    key: str
    path: str

class FileIconRegistry:
    def __init__(self):
        self._by_extension: Dict[str, IconEntry] = {}
        self._by_filename: Dict[str, IconEntry] = {}
        self._default_file: Optional[IconEntry] = None

    def register_extension(self, ext: str, icon_path: str):
        ext = ext.lower().lstrip('.')
        self._by_extension[ext] = IconEntry(ext, icon_path)

    def register_filename(self, filename: str, icon_path: str):
        self._by_filename[filename.lower()] = IconEntry(filename.lower(), icon_path)

    def set_default_file(self, icon_path: str):
        self._default_file = IconEntry('__default__', icon_path)

    def icon_for(self, file_path: Path) -> QIcon:
        name = file_path.name.lower()
        # 1. Exact filename
        if name in self._by_filename:
            return self._icon(self._by_filename[name].path)
        # 2. Extension
        ext = file_path.suffix.lower().lstrip('.')
        if ext in self._by_extension:
            return self._icon(self._by_extension[ext].path)
        # 3. Default
        if self._default_file:
            return self._icon(self._default_file.path)
        return QIcon()

    @staticmethod
    def _icon(rel_path: str) -> QIcon:
        return QIcon(str(Path(rel_path)))

# Shared singleton registry
file_icon_registry = FileIconRegistry()

class FileIconProvider(QFileIconProvider):
    """Icon provider that delegates to FileIconRegistry.
    For directories we return empty icon (chevrons already indicate folder state).
    """
    def __init__(self, registry: FileIconRegistry):
        super().__init__()
        self._registry = registry

    def icon(self, file_info):  # QFileInfo passed by Qt
        from PySide6.QtCore import QFileInfo
        if isinstance(file_info, QFileInfo):
            if file_info.isDir():
                return QIcon()  # keep folders icon-less (only chevrons)
            return self._registry.icon_for(Path(file_info.filePath()))
        return QIcon()
