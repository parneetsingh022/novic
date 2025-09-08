from __future__ import annotations
from PySide6.QtCore import Qt, QRect, QSize, QElapsedTimer
from PySide6.QtGui import QColor, QPainter, QTextFormat
from PySide6.QtWidgets import QAbstractScrollArea, QPlainTextEdit, QWidget, QTextEdit


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
        self._enable_overscroll = False  # disabled for stability
        self._bottom_overscroll = 0
        self._last_left_margin = -1
        self._last_bottom_margin = -1
        self._in_resize = False

        # ---- scrolling (direct wheel steps, fractional accumulation) ----
        # Base lines-per-notch for smooth scrolling; acceleration adapts when user spins fast
        self._wheel_lines_per_notch = 0.2
        self._wheel_accum = 0.0
        self._wheel_timer = QElapsedTimer()
        self._wheel_timer.invalidate()
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
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor('#2d3135'))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    # ---- convenience ---------------------------------------------------
    def setPlainText(self, text: str):  # type: ignore[override]
        super().setPlainText(text)
        self.document().setModified(False)
        self._apply_margins()
        self._recalc_overscroll()

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
        # Adaptive acceleration: quicker successive wheel events scroll farther (like VSCode)
        interval = 999
        if self._wheel_timer.isValid():
            interval = self._wheel_timer.elapsed()
        self._wheel_timer.restart()
        accel = 1.0
        if interval < 60:
            accel = 1.7
        elif interval < 100:
            accel = 1.4
        elif interval < 160:
            accel = 1.15
        effective_lpn = self._wheel_lines_per_notch * accel
        # Modifier keys: Ctrl for precision (slower), Shift for faster
        mods = event.modifiers()
        if mods & Qt.ControlModifier:
            effective_lpn *= 0.5
        if mods & Qt.ShiftModifier:
            effective_lpn *= 1.35
        # Compute fractional pixel movement for fine control
        delta_lines = -(delta_y / 120.0) * effective_lpn
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
    def setScrollLinesPerNotch(self, lines: float):
        if lines > 0:
            self._wheel_lines_per_notch = lines
            self._wheel_accum = 0.0
            self._wheel_timer.invalidate()

    # Convenience: set a comfort profile ("slow", "default", "fast")
    def setScrollProfile(self, profile: str):
        p = profile.lower()
        if p == "slow":
            self.setScrollLinesPerNotch(1.2)
            self.setScrollLinesPerNotch(0.8)
        elif p == "fast":
            self.setScrollLinesPerNotch(2.4)
            self.setScrollLinesPerNotch(1.9)
        else:
            self.setScrollLinesPerNotch(1.9)
            self.setScrollLinesPerNotch(1.2)


__all__ = ["CodeEditor"]
