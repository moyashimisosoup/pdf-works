"""Soft Outline combobox with a drawn chevron and non-native item popup.

Keeps Qt's native keyboard behavior, model, signals, focus management,
screen-edge placement, and high-DPI awareness, but changes the pixels.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QComboBox,
    QListView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)


class SoftItemDelegate(QStyledItemDelegate):
    """Paint a small-radius selection capsule and explicit current-value tick."""

    def __init__(self, combo: QComboBox):
        super().__init__(combo)
        self._combo = combo

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        return QSize(max(120, size.width() + 34), max(42, size.height() + 15))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = option.rect.adjusted(4, 2, -4, -2)
        selected = index.row() == self._combo.currentIndex()
        hover = bool(option.state & QStyle.StateFlag.State_MouseOver)
        highlighted = bool(option.state & QStyle.StateFlag.State_Selected)
        enabled = bool(option.state & QStyle.StateFlag.State_Enabled)
        if selected or highlighted:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#F0ECF4") if selected else QColor("#F6F4F8"))
            painter.drawRoundedRect(rect, 9, 9)
        elif hover:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#F8F6F9"))
            painter.drawRoundedRect(rect, 9, 9)
        painter.setPen(QColor("#351F39") if enabled else QColor("#9B949C"))
        font = option.font
        if selected:
            font.setWeight(font.Weight.Medium)
        painter.setFont(font)
        label = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        text_rect = rect.adjusted(13, 0, -33, 0)
        painter.drawText(text_rect,
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         painter.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight,
                                                          max(1, text_rect.width())))
        if selected:
            x, y = rect.right()-18, rect.center().y()
            pen = QPen(QColor("#726A95"), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF([
                QPointF(x-5, y), QPointF(x-1, y+4), QPointF(x+6, y-4),
            ]))
        painter.restore()


class SoftComboBox(QComboBox):
    """A QComboBox that doesn't use the platform-native popup delegate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("softCombo")
        self.setMinimumHeight(42)
        self.setMinimumWidth(112)
        self.setMaxVisibleItems(8)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        view = QListView(self)
        view.setMouseTracking(True)
        view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setFrameShape(QListView.Shape.NoFrame)
        view.setSpacing(0)
        view.setItemDelegate(SoftItemDelegate(self))
        self.setView(view)

    def showPopup(self) -> None:
        # QComboBox retains standard Escape/Enter/arrow/typing behavior.
        view = self.view()
        view.setMinimumWidth(max(self.width(), 130))
        super().showPopup()
        view.setCurrentIndex(self.model().index(self.currentIndex(), self.modelColumn()))
        view.viewport().update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            color = QColor("#AAA1AE")
        elif self.view().isVisible():
            color = QColor("#5B5179")
        else:
            color = QColor("#726A95")
        pen = QPen(color, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        center_x = self.width() - 19
        center_y = self.height() / 2
        sign = -1 if self.view().isVisible() else 1
        painter.drawPolyline(QPolygonF([
            QPointF(center_x - 5, center_y - 2 * sign),
            QPointF(center_x, center_y + 3 * sign),
            QPointF(center_x + 5, center_y - 2 * sign),
        ]))
        painter.end()
