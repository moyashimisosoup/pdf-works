"""Zoomable A-over-B preview with A-only mouse dragging.

The rendered first pages are display-only bitmaps. Geometry is kept in PDF
points, so dragging updates the exact millimeter offsets used by PDF export.
No PDF file is ever opened from the GUI thread.
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QTransform
from PySide6.QtWidgets import (
    QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView,
)

POINTS_PER_MM = 72.0 / 25.4


class AlignmentCanvas(QGraphicsView):
    """B stays fixed while a draggable A layer follows the millimeter inputs."""

    moved_mm = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(Qt.GlobalColor.white)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setRenderHints(self.renderHints())
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumSize(200, 210)
        self.setStyleSheet(
            "QGraphicsView { background:#FFFFFF;"
            " border:1px solid #D8D0D4; border-radius:10px; }"
        )
        self._b_item: QGraphicsPixmapItem | None = None
        self._a_item: QGraphicsPixmapItem | None = None
        self._reference_size: tuple[float, float] | None = None
        self._zoom = 1.0
        self._drag_from = None

    def pixmap(self) -> QPixmap:
        """Convenience for existing Qt preview checks."""
        return self._b_item.pixmap() if self._b_item else QPixmap()

    def set_pages(
        self,
        source: QImage,
        reference: QImage,
        reference_size: tuple[float, float],
    ):
        self.scene().clear()
        self._drag_from = None
        self._reference_size = reference_size
        self._b_item = self.scene().addPixmap(QPixmap.fromImage(reference))
        self._a_item = self.scene().addPixmap(QPixmap.fromImage(source))
        self._b_item.setZValue(0)
        self._a_item.setZValue(1)
        self._b_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        self._a_item.setTransformationMode(
            Qt.TransformationMode.SmoothTransformation
        )
        self.setSceneRect(QRectF(0, 0, reference.width(), reference.height()))
        self._fit_zoom(reset_center=True)

    def clear_pages(self):
        self.scene().clear()
        self._b_item = None
        self._a_item = None
        self._reference_size = None
        self._drag_from = None

    def set_zoom_percent(self, percent: int):
        if not 50 <= percent <= 600:
            return
        self._zoom = percent / 100.0
        self._fit_zoom(reset_center=False)

    def _fit_zoom(self, *, reset_center: bool = False):
        if self._b_item is None:
            return
        old_center = self.mapToScene(self.viewport().rect().center())
        scene = self.sceneRect()
        if scene.width() <= 0 or scene.height() <= 0:
            return
        # 100% = fit the entire reference page into the available viewport.
        viewport = self.viewport().size()
        fit = min(
            (viewport.width() - 12) / scene.width(),
            (viewport.height() - 12) / scene.height(),
        )
        self.setTransform(
            QTransform.fromScale(
                max(0.01, fit * self._zoom),
                max(0.01, fit * self._zoom),
            )
        )
        self.centerOn(scene.center() if reset_center else old_center)

    def set_opacity_percent(self, percent: int):
        if self._a_item is not None:
            self._a_item.setOpacity(max(0.1, min(0.9, percent / 100.0)))

    def set_placement(self, pdf_rect: tuple[float, float, float, float]):
        """Position A to the same geometry that the PDF exporter will use."""
        if not self._a_item or not self._b_item or not self._reference_size:
            return
        rw, rh = self._reference_size
        scene = self.sceneRect()
        x0, y0, x1, y1 = pdf_rect
        xscale = scene.width() / rw
        yscale = scene.height() / rh
        source = self._a_item.pixmap()
        if source.isNull():
            return
        self._a_item.setTransform(
            QTransform.fromScale(
                (x1 - x0) * xscale / source.width(),
                (y1 - y0) * yscale / source.height(),
            )
        )
        self._a_item.setPos(x0 * xscale, y0 * yscale)

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.isEnabled()
            and self._a_item is not None
        ):
            pos = self.mapToScene(event.position().toPoint())
            if self._a_item.sceneBoundingRect().contains(pos):
                self._drag_from = pos
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_from is not None and self._reference_size:
            here = self.mapToScene(event.position().toPoint())
            change = here - self._drag_from
            self._drag_from = here
            bounds = self.sceneRect()
            dx = change.x() * self._reference_size[0] / bounds.width() / POINTS_PER_MM
            dy = change.y() * self._reference_size[1] / bounds.height() / POINTS_PER_MM
            if dx or dy:
                self.moved_mm.emit(dx, dy)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_from is not None:
            self._drag_from = None
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._b_item is not None:
            self._fit_zoom()
