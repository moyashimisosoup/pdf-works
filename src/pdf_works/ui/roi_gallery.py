"""Non-modal ROI gallery: lazy asynchronous thumbnails, large preview and source jump.

Only QImage decoding happens off the UI thread. QPixmap/QIcon are constructed
on the GUI thread; no PDF opens or page rendering occur in this window.
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, QTimer, QSize, Signal, Slot
from PySide6.QtGui import QIcon, QImage, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from .widgets.combo_box import SoftComboBox

THUMB_LIMIT = 48
MAX_DECODE_PIXELS = 16_000_000


class _Decoded(QObject):
    finished = Signal(int, str, QImage)


class _ReadImage(QRunnable):
    """Decode and downscale one PNG without blocking the Qt event loop."""

    def __init__(self, index: int, kind: str, path: Path, bounds: QSize):
        super().__init__()
        self.index, self.kind, self.path, self.bounds = index, kind, path, bounds
        self.signals = _Decoded()

    def run(self):
        image = QImage()
        try:
            reader = QImageReader(str(self.path))
            size = reader.size()
            if (size.isValid() and size.width() > 0 and size.height() > 0
                    and size.width() * size.height() <= MAX_DECODE_PIXELS):
                scaled = size.scaled(self.bounds, Qt.AspectRatioMode.KeepAspectRatio)
                reader.setScaledSize(scaled)
                image = reader.read()
        except Exception:
            pass
        self.signals.finished.emit(self.index, self.kind, image)


class CropGallery(QDialog):
    """Standalone window with source-ID-safe jump and visible-only image loads."""

    source_requested = Signal(int)

    def __init__(self, image_files, source_ids, parent=None):
        super().__init__(parent)
        if not image_files or len(image_files) != len(source_ids):
            raise ValueError("A gallery requires a file and source page for each entry")
        self._paths = [Path(p) for p in image_files]
        self._sources = list(source_ids)
        self._loaded = OrderedDict()
        self._pending = {}
        self._preview_index = -1
        self.setWindowTitle("pdf-works | 切り出し一覧")
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(1040, 710)
        self.setMinimumSize(620, 430)
        self.setStyleSheet("""
            QDialog, QWidget { background:#FCFBF7; color:#351F39; }
            QListWidget { background:#FCFBF7; border:1px solid #D8D0D4;
                          border-radius:15px; outline:none; }
            QListWidget::item { border-radius:12px; margin:3px; padding:5px; }
            QListWidget::item:selected { background:#F0ECF4; color:#351F39; }
            QLabel#preview { background:white; border:1px solid #D8D0D4;
                             border-radius:16px; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        header = QHBoxLayout()
        title = QLabel(f"切り出し一覧 · {len(self._paths)}件")
        header.addWidget(title, 1)
        header.addWidget(QLabel("表示"))
        self.size_combo = SoftComboBox()
        for label, px in (("小", 96), ("中", 144), ("大", 184)):
            self.size_combo.addItem(label, px)
        self.size_combo.setCurrentIndex(1)
        self.size_combo.currentIndexChanged.connect(self._change_tile_size)
        header.addWidget(self.size_combo)
        close_button = QPushButton("閉じる")
        close_button.setMinimumWidth(close_button.sizeHint().width() + 16)
        close_button.clicked.connect(self.close)
        header.addWidget(close_button)
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.items = QListWidget()
        self.items.setViewMode(QListView.ViewMode.IconMode)
        self.items.setResizeMode(QListView.ResizeMode.Adjust)
        self.items.setMovement(QListView.Movement.Static)
        self.items.setWrapping(True)
        self.items.setWordWrap(False)
        self.items.setSpacing(7)
        self.items.setIconSize(QSize(144, 118))
        self.items.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.items.setSelectionMode(QListView.SelectionMode.SingleSelection)
        for idx, source in enumerate(self._sources):
            item = QListWidgetItem(f"{idx+1} · 元{source+1}")
            item.setData(Qt.ItemDataRole.UserRole, source)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(QSize(180, 160))
            self.items.addItem(item)
        splitter.addWidget(self.items)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(10, 4, 4, 4)
        self.preview = QLabel("切り出し画像を選択してください")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumWidth(250)
        self.preview.setWordWrap(False)
        preview_layout.addWidget(self.preview, 1)
        self.details = QLabel("ダブルクリックで元ページを表示")
        self.details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.details.setWordWrap(False)
        preview_layout.addWidget(self.details)
        splitter.addWidget(preview_container)
        splitter.setSizes([620, 390])
        root.addWidget(splitter, 1)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._request_visible)
        self.items.verticalScrollBar().valueChanged.connect(self._schedule_visible)
        self.items.currentRowChanged.connect(self._select_preview)
        self.items.itemDoubleClicked.connect(
            lambda item: self.source_requested.emit(item.data(Qt.ItemDataRole.UserRole))
        )
        self._change_tile_size()
        self.items.setCurrentRow(0)

    def _change_tile_size(self, *_):
        px = int(self.size_combo.currentData())
        self.items.setIconSize(QSize(px, max(60, int(px * .82))))
        for idx in range(self.items.count()):
            self.items.item(idx).setSizeHint(QSize(px+36, px+28))
        self._schedule_visible()

    def _schedule_visible(self, *_):
        self._timer.start()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_visible()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_visible()

    def _request_visible(self):
        viewport = self.items.viewport().rect()
        for idx in range(self.items.count()):
            item = self.items.item(idx)
            if not self.items.visualItemRect(item).intersects(viewport):
                continue
            if idx in self._loaded:
                continue
            self._schedule_read(idx, "thumb", QSize(184, 152))
        if self._preview_index >= 0:
            self._schedule_read(self._preview_index, "preview", QSize(780, 660))

    def _schedule_read(self, index: int, kind: str, size: QSize):
        key = (index, kind)
        if key in self._pending or (kind == "thumb" and index in self._loaded):
            return
        if kind == "preview" and self._preview_index != index:
            return
        task = _ReadImage(index, kind, self._paths[index], size)
        self._pending[key] = task  # Keep Python signal objects alive.
        task.signals.finished.connect(self._decoded)
        QThreadPool.globalInstance().start(task)

    @Slot(int, str, QImage)
    def _decoded(self, index: int, kind: str, image: QImage):
        self._pending.pop((index, kind), None)
        if image.isNull():
            if kind == "preview" and self._preview_index == index:
                self.preview.setText("画像を表示できません")
            return
        if kind == "preview":
            if index == self._preview_index:
                self.preview.setPixmap(QPixmap.fromImage(image))
            return
        self._loaded[index] = True
        self._loaded.move_to_end(index)
        self.items.item(index).setIcon(QIcon(QPixmap.fromImage(image)))
        while len(self._loaded) > THUMB_LIMIT:
            old, _ = self._loaded.popitem(last=False)
            self.items.item(old).setIcon(QIcon())

    def _select_preview(self, index: int):
        self._preview_index = index
        self.preview.clear()
        if index < 0:
            return
        self.preview.setText("読み込み中…")
        self.details.setText(f"{index+1}番目 · 元{self._sources[index]+1}ページ")
        self._schedule_read(index, "preview", QSize(780, 660))
        self._schedule_visible()
