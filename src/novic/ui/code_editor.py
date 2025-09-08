from __future__ import annotations
from PySide6.QtCore import Qt, QRect, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QTextFormat, QGuiApplication, QSyntaxHighlighter, QTextCharFormat

# Lazy import holder for syntax to avoid cost if unused
try:
    from novic.syntax import SyntaxRegistry, load_all_languages
    _SYNTAX_REGISTRY = load_all_languages()
except Exception:  # pragma: no cover - syntax not critical
    _SYNTAX_REGISTRY = None
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit


class _LineNumberArea(QWidget):
    def __init__(self, editor: 'CodeEditor'):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):  # type: ignore[override]
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # type: ignore[override]
        self._editor._paint_line_numbers(event)


class CodeEditor(QPlainTextEdit):
    """Plain text editor with line numbers and lightweight overscroll.

    Focus on performance: avoid heavy work in paint events; recompute geometry only on
    resize and block count changes. Overscroll implemented via bottom viewport margin, not
    by adjusting scrollbar range inside paint (prevents lag & crashes).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # ---- core state ----
        self._line_number_area = _LineNumberArea(self)
        self._enable_overscroll = False
        self._bottom_overscroll = 0
        self._last_left_margin = -1
        self._last_bottom_margin = -1
        self._in_resize = False
        # syntax state
        self._active_language = None
        self._highlighter = _SyntaxHighlighter(self.document())

        # ---- scrolling (direct wheel steps, fractional accumulation) ----
        try:
            system_lines = QGuiApplication.styleHints().wheelScrollLines() or 3
        except Exception:
            system_lines = 3
        if system_lines <= 0:
            system_lines = 3
        self._base_wheel_lines = float(system_lines)
        self._wheel_lines_per_notch = self._base_wheel_lines
        self._wheel_accum = 0.0
        self.verticalScrollBar().setSingleStep(self.fontMetrics().height())

        # ---- performance hints ----
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        # ---- font ----
        try:
            f = self.font()
            f.setFamily("Consolas")
            if f.pointSize() <= 0:
                f.setPointSize(11)
            else:
                f.setPointSize(max(11, f.pointSize()))
            self.setFont(f)
        except Exception:
            pass

        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)

        # ---- signals ----
        self.blockCountChanged.connect(self._on_block_count_changed)
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.textChanged.connect(self._on_text_changed)

        # ---- initial visuals ----
        self._apply_margins()
        self._highlight_current_line()
        self.setStyleSheet(
            "QPlainTextEdit { background:#1f2123; color:#e3e5e8; border:none; padding:6px 0 6px 0; }"
        )

    # ---- geometry & margins -------------------------------------------
    def line_number_area_width(self) -> int:
        digits = 1
        max_block = max(1, self.blockCount())
        while max_block >= 10:
            max_block //= 10
            digits += 1
        return 8 + self.fontMetrics().horizontalAdvance('9') * digits

    def _apply_margins(self):
        left = self.line_number_area_width()
        if left != self._last_left_margin or self._bottom_overscroll != self._last_bottom_margin:
            self.setViewportMargins(left, 0, 0, self._bottom_overscroll)
            self._last_left_margin = left
            self._last_bottom_margin = self._bottom_overscroll
        # Geometry update is cheap; always update to sync height
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), left, cr.height()))

    def _recalc_overscroll(self):
        # Overscroll disabled for now; keep placeholder for future safe implementation.
        if self._bottom_overscroll != 0:
            self._bottom_overscroll = 0
            self._apply_margins()

    # ---- event hooks ---------------------------------------------------
    def resizeEvent(self, event):  # type: ignore[override]
        if self._in_resize:
            # Allow base class to process but avoid re-entrant margin logic
            super().resizeEvent(event)
            return
        self._in_resize = True
        try:
            super().resizeEvent(event)
            # No overscroll adjustments; just ensure margins reflect gutter width.
            self._apply_margins()
        finally:
            self._in_resize = False

    def _on_block_count_changed(self, _):
        self._apply_margins()
        # block count changes may affect scroll height – overscroll recalculated
        self._recalc_overscroll()

    def _on_update_request(self, rect, dy):  # type: ignore[override]
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
    # Avoid calling _apply_margins() here; it can trigger resize recursion.

    # ---- painting ------------------------------------------------------
    def _paint_line_numbers(self, event):
        painter = QPainter(self._line_number_area)
        # Explicitly paint gutter background to avoid uninitialized artifacts on some systems
        painter.fillRect(event.rect(), QColor('#1f2123'))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        fm = self.fontMetrics()
        ln_color = QColor('#7d848a')
        active_color = QColor('#cfd2d6')
        width = self._line_number_area.width() - 6
        viewport_bottom = event.rect().bottom()
        cursor_block = self.textCursor().blockNumber()

        while block.isValid() and top <= viewport_bottom:
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(active_color if block_number == cursor_block else ln_color)
                painter.drawText(0, top, width, fm.height(), Qt.AlignRight | Qt.AlignVCenter, number)
            block = block.next()
            block_number += 1
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    # ---- highlight current line ---------------------------------------
    def _highlight_current_line(self):
        # Only current line background (syntax colors handled by highlighter)
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        line_sel = QTextEdit.ExtraSelection()
        line_sel.format.setBackground(QColor('#2d3135'))
        line_sel.format.setProperty(QTextFormat.FullWidthSelection, True)
        line_sel.cursor = self.textCursor()
        line_sel.cursor.clearSelection()
        self.setExtraSelections([line_sel])

    # ---- convenience ---------------------------------------------------
    def setPlainText(self, text: str):  # type: ignore[override]
        super().setPlainText(text)
        self.document().setModified(False)
        self._apply_margins()
        self._recalc_overscroll()
        # rehighlight if language active
        if self._active_language:
            self._highlighter.schedule_refresh(self._active_language)

    # ---- syntax highlighting API -------------------------------------
    def applySyntaxByName(self, name: str):
        if not _SYNTAX_REGISTRY:
            return
        lang = _SYNTAX_REGISTRY.get(name)
        if not lang:
            return
        self._active_language = lang
        self._highlighter.schedule_refresh(lang, immediate=True)

    def applySyntaxForExtension(self, ext: str):
        if not _SYNTAX_REGISTRY:
            return
        lang = _SYNTAX_REGISTRY.get_for_extension(ext)
        if not lang:
            return
        self._active_language = lang
        self._highlighter.schedule_refresh(lang, immediate=True)

    def _on_text_changed(self):
        if self._active_language:
            self._highlighter.schedule_refresh(self._active_language)
        self._highlight_current_line()

    # ---- lightweight wheel handling (no animation) -------------------
    def wheelEvent(self, event):  # type: ignore[override]
        # Pixel based (high-res trackpad) -> default for natural smoothness
        if event.pixelDelta().y():
            return super().wheelEvent(event)
        delta_y = event.angleDelta().y()
        if delta_y == 0:
            return super().wheelEvent(event)
        sb = self.verticalScrollBar()
        line_h = self.fontMetrics().height()
        # Determine effective lines per notch (modifiers emulate VSCode style acceleration)
        lines_per_notch = self._wheel_lines_per_notch
        mods = event.modifiers()
        if mods & Qt.ShiftModifier:  # fast scroll
            lines_per_notch *= 3.0
        elif mods & Qt.AltModifier:  # slow scroll
            lines_per_notch = max(1.0, lines_per_notch * 0.5)

        # Compute fractional pixel movement for fine control
        delta_lines = -(delta_y / 120.0) * lines_per_notch
        pixels = delta_lines * line_h + self._wheel_accum
        step = int(pixels)
        self._wheel_accum = pixels - step
        if step == 0:
            # Nothing whole to apply this event; accumulate remainder for next wheel
            event.accept()
            return
        sb.setValue(max(sb.minimum(), min(sb.maximum(), sb.value() + step)))
        event.accept()

    # Public API to adjust scroll speed at runtime
    def setScrollLinesPerNotch(self, lines: float | None = None, *, use_system: bool = False):
        """Adjust base scrolling speed.

        lines: explicit lines per wheel notch (overrides system if provided)
        use_system: when True, revert to system wheelScrollLines()
        """
        if use_system:
            try:
                sys_lines = QGuiApplication.styleHints().wheelScrollLines()
                if sys_lines > 0:
                    self._base_wheel_lines = float(sys_lines)
            except Exception:
                pass
            self._wheel_lines_per_notch = self._base_wheel_lines
        elif lines and lines > 0:
            self._wheel_lines_per_notch = float(lines)
        self._wheel_accum = 0.0


__all__ = ["CodeEditor"]


class _SyntaxHighlighter(QSyntaxHighlighter):
    """Simple syntax highlighter with debounced lexing and block-local formatting."""

    def __init__(self, doc):
        super().__init__(doc)
        self._tokens: list[tuple] = []
        self._style: dict = {}
        self._starts: list[int] = []
        self._pending_language = None
        self._debounce_timer: QTimer | None = None
        self._busy = False

    def schedule_refresh(self, language, immediate: bool = False):
        self._pending_language = language
        if immediate:
            self._run_refresh()
            return
        if self._debounce_timer is None:
            self._debounce_timer = QTimer()
            self._debounce_timer.setSingleShot(True)
            self._debounce_timer.timeout.connect(self._run_refresh)
        # restart timer (150ms debounce)
        self._debounce_timer.start(150)

    def _run_refresh(self):
        if self._busy:
            # avoid re-entrancy; schedule again
            if self._debounce_timer:
                self._debounce_timer.start(50)
            return
        lang = self._pending_language
        if not lang:
            return
        self._busy = True
        try:
            try:
                text = self.document().toPlainText()
            except Exception:
                text = ""
            # Hard limits to avoid huge regex slowdown
            if len(text) > 500_000:
                # Disable highlighting for very large files for stability
                self._tokens = []
                self._starts = []
                self._style = {}
                self.rehighlight()
                return
            sample = text[:50_000]
            try:
                tokens = lang.lexer(sample)[:4000]
            except Exception:
                tokens = []
            self._tokens = tokens
            self._style = getattr(lang, 'style', {}) or {}
            self._starts = [t[2] for t in self._tokens]
            self.rehighlight()
        finally:
            self._busy = False

    def highlightBlock(self, text):  # type: ignore[override]
        if not self._tokens:
            return
        block_start = self.currentBlock().position()
        block_end = block_start + len(text)
        import bisect
        idx = bisect.bisect_left(self._starts, block_start) - 1
        if idx < 0:
            idx = 0
        n = len(self._tokens)
        while idx < n:
            kind, _value, start, end = self._tokens[idx]
            if start >= block_end:
                break
            if end > block_start:
                color = None
                if isinstance(self._style, dict):
                    color = self._style.get(kind, {}).get('color')
                if color:
                    fmt = QTextCharFormat()
                    fmt.setForeground(QColor(color))
                    s = max(start - block_start, 0)
                    e = min(end - block_start, len(text))
                    if e > s:
                        self.setFormat(s, e - s, fmt)
            idx += 1
