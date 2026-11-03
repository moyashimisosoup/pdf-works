"""Clipped-view PDF viewer with optional normalized rectangle selection.

Images still arrive from the separate PDF process. Region selection is a
lightweight QGraphicsRectItem overlay, never a full-resolution crop on the UI thread.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene, QGraphicsView


class PdfViewer(QGraphicsView):
    region_requested = Signal(tuple, float)
    roi_changed = Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setStyleSheet("QGraphicsView { background:#FCFBF7; border:0px; }")
        self._zoom = 1.0
        self._dimensions: tuple[float, float] | None = None
        self._pixitem: QGraphicsPixmapItem | None = None
        self._roi_item: QGraphicsRectItem | None = None
        self._roi: tuple[float, float, float, float] | None = None
        self._roi_selecting = False
        self._drag_start: QPointF | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(130)
        self._timer.timeout.connect(self._request_visible)
        self.horizontalScrollBar().valueChanged.connect(self._schedule)
        self.verticalScrollBar().valueChanged.connect(self._schedule)

    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def roi(self) -> tuple[float, float, float, float] | None:
        return self._roi

    def enable_roi_selection(self, enabled: bool):
        self._roi_selecting = bool(enabled)
        self._drag_start = None
        self.setDragMode(
            QGraphicsView.DragMode.NoDrag if enabled
            else QGraphicsView.DragMode.ScrollHandDrag
        )
        self.viewport().setCursor(
            Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor
        )
        self._draw_roi()

    def set_roi(self, normalized: tuple[float, float, float, float]):
        from ..core.crop import NormalizedROI
        roi = NormalizedROI(*normalized)
        self._roi = (roi.left, roi.top, roi.right, roi.bottom)
        self._draw_roi()
        self.roi_changed.emit(self._roi)

    def clear_roi(self):
        self._roi = None
        self._drag_start = None
        self._draw_roi()
        self.roi_changed.emit(())

    def set_page(self, width: float, height: float):
        self._timer.stop()
        self.scene().clear()
        self._pixitem = None
        self._roi_item = None
        self._dimensions = (width, height)
        self.scene().setSceneRect(0, 0, width, height)
        self.scene().addRect(
            QRectF(0, 0, width, height),
            QPen(QColor("#D8D0D4"), 0),
            QBrush(QColor("#FFFFFF")),
        )
        self._draw_roi()
        self._schedule()

    def reset_document(self):
        self._timer.stop()
        self.scene().clear()
        self._pixitem = None
        self._roi_item = None
        self._dimensions = None
        self._roi = None
        self._drag_start = None
        self.roi_changed.emit(())

    def set_zoom(self, value: float):
        if not 0.5 <= value <= 3.0:
            return
        self._zoom = value
        self.setTransform(QTransform.fromScale(value, value))
        self._schedule()

    def _schedule(self, *args):
        if self._dimensions:
            self._timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule()

    def _request_visible(self):
        if not self._dimensions:
            return
        viewport = self.mapToScene(self.viewport().rect()).boundingRect()
        margin = 40.0 / self._zoom
        bounds = QRectF(0, 0, *self._dimensions)
        region = viewport.adjusted(-margin, -margin, margin, margin).intersected(bounds)
        if region.isEmpty():
            return
        budget = region.width() * region.height() * self._zoom * self._zoom
        scale = self._zoom
        if budget > 5_000_000:
            scale *= (5_000_000 / budget) ** .5
        self.region_requested.emit(
            (region.left(), region.top(), region.right(), region.bottom()), scale
        )

    def show_image(self, pixmap: QPixmap, x: float, y: float, scale: float):
        if not self._dimensions:
            return
        if self._pixitem is not None:
            self.scene().removeItem(self._pixitem)
        self._pixitem = self.scene().addPixmap(pixmap)
        self._pixitem.setPos(x, y)
        self._pixitem.setScale(1.0 / scale)
        self._pixitem.setZValue(1)
        self._draw_roi()

    def _draw_roi(self, rect: QRectF | None = None):
        if self._roi_item is not None:
            self.scene().removeItem(self._roi_item)
            self._roi_item = None
        if not self._dimensions:
            return
        w, h = self._dimensions
        if rect is None and self._roi is not None:
            left, top, right, bottom = self._roi
            rect = QRectF(left * w, top * h, (right - left) * w, (bottom - top) * h)
        if rect is None or rect.isEmpty():
            return
        pen = QPen(QColor("#726A95"), 1.8, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        self._roi_item = self.scene().addRect(
            rect, pen, QBrush(QColor(114, 106, 149, 38))
        )
        self._roi_item.setZValue(5)

    def _clamped_point(self, event) -> QPointF:
        w, h = self._dimensions
        pos = self.mapToScene(event.position().toPoint())
        return QPointF(min(w, max(0, pos.x())), min(h, max(0, pos.y())))

    def mousePressEvent(self, event):
        if (self._roi_selecting and self._dimensions
                and event.button() == Qt.MouseButton.LeftButton):
            p = self.mapToScene(event.position().toPoint())
            if QRectF(0, 0, *self._dimensions).contains(p):
                self._drag_start = self._clamped_point(event)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None and self._dimensions:
            p = self._clamped_point(event)
            self._draw_roi(QRectF(self._drag_start, p).normalized())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None and self._dimensions:
            origin = self._drag_start
            self._drag_start = None
            if event.button() != Qt.MouseButton.LeftButton:
                self._draw_roi()
                event.accept()
                return
            rect = QRectF(origin, self._clamped_point(event)).normalized()
            if rect.width() >= 4 and rect.height() >= 4:
                w, h = self._dimensions
                self.set_roi((
                    rect.left() / w, rect.top() / h,
                    rect.right() / w, rect.bottom() / h,
                ))
            else:
                self._draw_roi()
            event.accept()
            return
        super().mouseReleaseEvent(event)
