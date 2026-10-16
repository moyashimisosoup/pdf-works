"""Clipped-view PDF viewer. Rendering always happens outside the Qt process."""
from __future__ import annotations
from PySide6.QtCore import QRectF,QTimer,Signal
from PySide6.QtGui import QColor,QBrush,QPen,QPixmap,QTransform
from PySide6.QtWidgets import QGraphicsPixmapItem,QGraphicsScene,QGraphicsView

class PdfViewer(QGraphicsView):
    region_requested=Signal(tuple,float)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setStyleSheet("QGraphicsView { background:#FCFBF7; border:0px; }")
        self._zoom=1.0
        self._dimensions:tuple[float,float]|None=None
        self._pixitem:QGraphicsPixmapItem|None=None
        self._timer=QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(130)
        self._timer.timeout.connect(self._request_visible)
        self.horizontalScrollBar().valueChanged.connect(self._schedule)
        self.verticalScrollBar().valueChanged.connect(self._schedule)

    @property
    def zoom(self)->float: return self._zoom

    def set_page(self,width:float,height:float):
        self._timer.stop()
        self.scene().clear()
        self._pixitem=None
        self._dimensions=(width,height)
        self.scene().setSceneRect(0,0,width,height)
        self.scene().addRect(QRectF(0,0,width,height),QPen(QColor("#D8D0D4"),0),QBrush(QColor("#FFFFFF")))
        self._schedule()

    def reset_document(self):
        self._timer.stop()
        self.scene().clear()
        self._pixitem=None
        self._dimensions=None

    def set_zoom(self,value:float):
        if not 0.5<=value<=3.0: return
        self._zoom=value
        self.setTransform(QTransform.fromScale(value,value))
        self._schedule()

    def _schedule(self,*args):
        if self._dimensions: self._timer.start()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._schedule()

    def _request_visible(self):
        if not self._dimensions: return
        viewport=self.mapToScene(self.viewport().rect()).boundingRect()
        margin=40.0/self._zoom
        bounds=QRectF(0,0,*self._dimensions)
        region=viewport.adjusted(-margin,-margin,margin,margin).intersected(bounds)
        if region.isEmpty(): return
        budget=region.width()*region.height()*self._zoom*self._zoom
        scale=self._zoom
        if budget>5_000_000:
            scale*=(5_000_000/budget)**0.5
        self.region_requested.emit((region.left(),region.top(),region.right(),region.bottom()),scale)

    def show_image(self,pixmap:QPixmap,x:float,y:float,scale:float):
        if not self._dimensions: return
        if self._pixitem is not None: self.scene().removeItem(self._pixitem)
        self._pixitem=self.scene().addPixmap(pixmap)
        self._pixitem.setPos(x,y)
        self._pixitem.setScale(1.0/scale)
        self._pixitem.setZValue(1)
