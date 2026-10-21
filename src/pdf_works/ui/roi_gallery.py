"""Non-modal ROI gallery: lazy asynchronous thumbnails, large preview and source jump.

Only QImage decoding happens off the UI thread. QPixmap/QIcon are constructed
on the GUI thread; no PDF opens or page rendering occur in this window.
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, QTimer, QSize, Signal, Slot
from PySide6.QtGui import QColor, QIcon, QImage, QImageReader, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListView, QListWidget, QListWidgetItem,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from .widgets.combo_box import SoftComboBox
from .button_theme import BUTTON_STYLE
from .theme import COMBO_STYLE

THUMB_LIMIT = 48
MAX_PENDING = 3
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
    pdf_requested = Signal()
    layout_changed = Signal(list, list)

    def __init__(self, image_files, source_ids, parent=None, *, order=None, excluded=None):
        super().__init__(parent)
        if not image_files or len(image_files) != len(source_ids):
            raise ValueError("A gallery requires a file and source page for each entry")
        self._paths = [Path(p) for p in image_files]
        self._sources = list(source_ids)
        count = len(self._paths)
        self._order = list(range(count)) if order is None else list(order)
        self._excluded = set() if excluded is None else set(excluded)
        if (len(self._order) != count or set(self._order) != set(range(count))
                or len(set(self._order)) != count
                or not self._excluded.issubset(set(range(count)))):
            raise ValueError("Invalid gallery order or excluded image IDs")
        self._loaded = OrderedDict()
        self._pending = {}
        self._preview_index = -1
        self._preview_image = QImage()
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
        """ + BUTTON_STYLE + COMBO_STYLE)
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
        pdf_button = QPushButton("PDF保存")
        pdf_button.setObjectName("primary")
        pdf_button.setMinimumWidth(pdf_button.sizeHint().width() + 16)
        pdf_button.setToolTip("A4縦・2列×4行の一覧PDFを新しいファイルに保存")
        pdf_button.clicked.connect(lambda checked=False: self.pdf_requested.emit())
        header.addWidget(pdf_button)
        self.pdf_button = pdf_button
        close_button = QPushButton("閉じる")
        close_button.setMinimumWidth(close_button.sizeHint().width() + 16)
        close_button.clicked.connect(self.close)
        header.addWidget(close_button)
        root.addLayout(header)
        operations = QHBoxLayout()
        operations.setSpacing(6)
        self.up_button = QPushButton("前へ")
        self.down_button = QPushButton("後へ")
        self.exclude_button = QPushButton("除外")
        self.restore_button = QPushButton("全件復元")
        self.counter = QLabel("")
        self.counter.setWordWrap(False)
        for button in (self.up_button, self.down_button,
                       self.exclude_button, self.restore_button):
            button.setMinimumWidth(button.sizeHint().width() + 12)
            operations.addWidget(button)
        operations.addWidget(self.counter, 1)
        root.addLayout(operations)
        self.up_button.clicked.connect(lambda: self._move_item(-1))
        self.down_button.clicked.connect(lambda: self._move_item(1))
        self.exclude_button.clicked.connect(self._toggle_excluded)
        self.restore_button.clicked.connect(self._restore_all)

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
        self._placeholder_icon = self._make_placeholder()
        for uid in self._order:
            item = QListWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, uid)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setIcon(self._placeholder_icon)
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
            lambda item: self.source_requested.emit(
                self._sources[item.data(Qt.ItemDataRole.UserRole)]
            )
        )
        self.items.currentRowChanged.connect(self._update_action_buttons)
        self._renumber()
        self._change_tile_size()
        self.items.setCurrentRow(0)
        self._update_action_buttons()

    def _renumber(self):
        for row in range(self.items.count()):
            item = self.items.item(row)
            uid = item.data(Qt.ItemDataRole.UserRole)
            mark = "［除外］" if uid in self._excluded else ""
            item.setText(f"{row+1} · 元{self._sources[uid]+1}{mark}")
            item.setForeground(QColor("#A49BA8" if uid in self._excluded else "#351F39"))
        active = self.items.count() - len(self._excluded)
        self.counter.setText(f"PDF対象 {active}/{self.items.count()}")
        self.pdf_button.setEnabled(active > 0)
        self.restore_button.setEnabled(bool(self._excluded))

    def _update_action_buttons(self, *_):
        row = self.items.currentRow()
        valid = 0 <= row < self.items.count()
        self.up_button.setEnabled(valid and row > 0)
        self.down_button.setEnabled(valid and row < self.items.count()-1)
        self.exclude_button.setEnabled(valid)
        if valid:
            uid = self.items.item(row).data(Qt.ItemDataRole.UserRole)
            self.exclude_button.setText("復元" if uid in self._excluded else "除外")

    def _changed(self):
        self._order = [self.items.item(i).data(Qt.ItemDataRole.UserRole)
                       for i in range(self.items.count())]
        self._renumber()
        self._update_action_buttons()
        self.layout_changed.emit(list(self._order), sorted(self._excluded))
        self._schedule_visible()

    def export_entries(self):
        """Only included files, in the user's displayed order."""
        ids = [uid for uid in self._order if uid not in self._excluded]
        return ([str(self._paths[uid]) for uid in ids],
                [self._sources[uid] for uid in ids])

    def _move_item(self, delta: int):
        row = self.items.currentRow()
        target = row + delta
        if row < 0 or not 0 <= target < self.items.count():
            return
        item = self.items.takeItem(row)
        self.items.insertItem(target, item)
        self.items.setCurrentRow(target)
        self._changed()

    def _toggle_excluded(self):
        row = self.items.currentRow()
        if row < 0:
            return
        uid = self.items.item(row).data(Qt.ItemDataRole.UserRole)
        if uid in self._excluded:
            self._excluded.remove(uid)
        else:
            self._excluded.add(uid)
        self._changed()

    def _restore_all(self):
        if self._excluded:
            self._excluded.clear()
            self._changed()

    @staticmethod
    def _make_placeholder():
        pixmap = QPixmap(184, 152)
        pixmap.fill(QColor("#FCFBF7"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#D8D0D4"), 2))
        painter.setBrush(QColor("#F8F6FA"))
        painter.drawRoundedRect(18, 7, 148, 135, 12, 12)
        painter.setPen(QPen(QColor("#C9BFCE"), 4))
        for idx, length in enumerate((88, 105, 68)):
            y = 46 + idx * 20
            painter.drawLine(42, y, 42 + length, y)
        painter.end()
        return QIcon(pixmap)

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
        self._display_preview()
        self._schedule_visible()

    def _display_preview(self):
        if not self._preview_image.isNull():
            pixmap = QPixmap.fromImage(self._preview_image)
            self.preview.setPixmap(pixmap.scaled(
                self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))

    def _request_visible(self):
        if self._preview_index >= 0:
            self._schedule_read(self._preview_index, "preview", QSize(780, 660))
        viewport = self.items.viewport().rect()
        for row in range(self.items.count()):
            item = self.items.item(row)
            if not self.items.visualItemRect(item).intersects(viewport):
                continue
            uid = item.data(Qt.ItemDataRole.UserRole)
            if uid in self._loaded:
                continue
            self._schedule_read(uid, "thumb", QSize(184, 152))

    def _schedule_read(self, index: int, kind: str, size: QSize):
        key = (index, kind)
        if (key in self._pending or len(self._pending) >= MAX_PENDING
                or (kind == "thumb" and index in self._loaded)):
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
        self._schedule_visible()
        if image.isNull():
            if kind == "preview" and self._preview_index == index:
                self.preview.setText("画像を表示できません")
            return
        if kind == "preview":
            if index == self._preview_index:
                self._preview_image = image
                self._display_preview()
            return
        self._loaded[index] = True
        self._loaded.move_to_end(index)
        for row in range(self.items.count()):
            item = self.items.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == index:
                item.setIcon(QIcon(QPixmap.fromImage(image)))
                break
        while len(self._loaded) > THUMB_LIMIT:
            old, _ = self._loaded.popitem(last=False)
            for row in range(self.items.count()):
                item = self.items.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == old:
                    item.setIcon(self._placeholder_icon)
                    break

    def _select_preview(self, index: int):
        uid = (self.items.item(index).data(Qt.ItemDataRole.UserRole)
               if 0 <= index < self.items.count() else -1)
        self._preview_index = uid
        self._preview_image = QImage()
        self.preview.clear()
        if index < 0:
            return
        self.preview.setText("読み込み中…")
        self.details.setText(f"{index+1}番目 · 元{self._sources[uid]+1}ページ")
        self._schedule_read(uid, "preview", QSize(780, 660))
        self._schedule_visible()
