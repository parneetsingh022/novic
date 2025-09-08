from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy, QComboBox
from PySide6.QtCore import Qt, QSize

try:
    from novic.syntax import load_all_languages
    _LANG_REG = load_all_languages()
except Exception:  # pragma: no cover
    _LANG_REG = None


class StatusFooter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self.setStyleSheet("background:#2b2d30; border-top:1px solid #3a3d41;")
        # Ensure footer stretches full width
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Allow stylesheet background to paint entire widget
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(12)
        self.label = QLabel("Ready", self)
        self.label.setStyleSheet("color:#8d949a; font-size:10px;")
        layout.addWidget(self.label)
        layout.addStretch()

        # Syntax selector
        self.syntax_combo = QComboBox(self)
        self.syntax_combo.setFixedHeight(16)
        self.syntax_combo.setStyleSheet("QComboBox { background:#33363a; color:#c7ccd1; font-size:10px; border:1px solid #3f4246; padding:0 4px;} QComboBox::drop-down{width:14px;}")
        self.syntax_combo.addItem("Plain Text")
        if _LANG_REG:
            for lang in sorted(_LANG_REG.languages(), key=lambda l: l.name.lower()):
                self.syntax_combo.addItem(lang.name)
        self.syntax_combo.currentTextChanged.connect(self._on_language_changed)
        layout.addWidget(self.syntax_combo)

    def set_status(self, text: str):
        self.label.setText(text)

    def sizeHint(self):  # type: ignore[override]
        # Suggest expansive width while keeping fixed height
        pw = self.parent().width() if self.parent() else 600
        return QSize(pw, 18)

    def minimumSizeHint(self):  # type: ignore[override]
        return QSize(0, 18)

    # External hookup for editor instance
    def attach_editor(self, editor):
        self._editor = editor
        # sync combo to editor's active language if available
        try:
            lang = getattr(getattr(editor, '_active_language', None), 'name', None)
            if lang and self.syntax_combo.findText(lang) >= 0:
                was = self.syntax_combo.blockSignals(True)
                self.syntax_combo.setCurrentText(lang)
                self.syntax_combo.blockSignals(was)
            elif not lang:
                was = self.syntax_combo.blockSignals(True)
                self.syntax_combo.setCurrentIndex(0)
                self.syntax_combo.blockSignals(was)
        except Exception:
            pass

    def _on_language_changed(self, name: str):
        if not hasattr(self, '_editor') or name == 'Plain Text':
            return
        # try to apply by name
        apply_method = getattr(self._editor, 'applySyntaxByName', None)
        if callable(apply_method):
            apply_method(name)


__all__ = ["StatusFooter"]
