"""Qt Widgets alpha UI: lightweight PDF viewer and lazy thumbnails."""
from __future__ import annotations
from collections import deque
from pathlib import Path
from PySide6.QtCore import QTimer,QSize,Qt,QSettings
from PySide6.QtGui import QFont,QFontDatabase,QIcon,QImage,QPixmap
from PySide6.QtWidgets import (QAbstractItemView,QApplication,QComboBox,QFileDialog,
    QFrame,QHBoxLayout,QLabel,QListWidget,QListWidgetItem,QMainWindow,
    QMessageBox,QPushButton,QSplitter,QVBoxLayout,QWidget)
from .viewer import PdfViewer
from .button_theme import BUTTON_STYLE
from .theme import COMBO_STYLE
from .widgets.combo_box import SoftComboBox
from .typography import PRESETS, font_for_preset, font_status
from ..workers.bridge import PdfBridge
from ..core.file_size import format_file_size

STYLE="""
QMainWindow,QWidget {background:#FCFBF7;color:#351F39;}
QLabel {border:0px;}
QFrame#panel {border:1px solid #D8D0D4;border-radius:22px;}
QListWidget {background:#FCFBF7;border:0px;outline:none;}
QListWidget::item {border-radius:12px;margin:3px;padding:4px;}
QListWidget::item:selected {background:#F0EEF4;color:#351F39;}
QStatusBar {background:#FCFBF7;color:#726A95;}
QScrollBar:vertical {background:transparent;width:12px;}
QScrollBar::handle:vertical {background:#D8D0D4;border-radius:5px;min-height:20px;margin:2px;}
"""

def japanese_font()->QFont:
    # Consistent startup font: loaded from a local file when available.
    return font_for_preset("standard")

def rgb_to_pixmap(image:dict)->QPixmap:
    qimg=QImage(image["samples"],image["width"],image["height"],image["stride"],
                QImage.Format.Format_RGB888).copy()
    return QPixmap.fromImage(qimg)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pdf-works | Soft Outline")
        self.resize(1160,780)
        self.setMinimumSize(560,440)
        self.setStyleSheet(STYLE + BUTTON_STYLE + COMBO_STYLE)
        self._pdf_path=None
        self._generation=0
        self._sizes=[]
        self._current_page=0
        self._latest_image_req=None
        self._thumb_ready=set()
        self._pending_thumbs=set()
        self._thumb_queue=deque()
        self._font_preset = str(QSettings("pdf-works", "desktop").value("text_weight", "standard"))
        if self._font_preset not in PRESETS:
            self._font_preset = "standard"
        self._bridge=PdfBridge(self)
        self._bridge.result_ready.connect(self._on_worker_reply)
        self._bridge.worker_failed.connect(self._on_worker_failed)
        self._build_ui()
        self._apply_font_preset(self._font_preset, save=False)
        QTimer.singleShot(0,self._start_worker)

    def _build_ui(self):
        root=QWidget()
        self.setCentralWidget(root)
        layout=QVBoxLayout(root)
        layout.setContentsMargins(18,14,18,10)
        layout.setSpacing(14)
        header=QHBoxLayout()
        self.title_label=QLabel("pdf-works")
        header.addWidget(self.title_label)
        self.filename=QLabel("PDFを開いてください")
        self.filename.setStyleSheet("color:#726A95")
        header.addWidget(self.filename,stretch=1)
        self.size_label=QLabel("")
        self.size_label.setWordWrap(False)
        self.size_label.setStyleSheet("color:#726A95;")
        header.addWidget(self.size_label)
        self.open_button=QPushButton("開く")
        self.open_button.setObjectName("primary")
        self.open_button.clicked.connect(self._choose_pdf)
        header.addWidget(self.open_button)
        layout.addLayout(header)

        bar=QHBoxLayout()
        bar.setSpacing(8)
        self.prev_button=QPushButton("‹ 前")
        self.next_button=QPushButton("次 ›")
        self.prev_button.clicked.connect(lambda:self._select_page(self._current_page-1))
        self.next_button.clicked.connect(lambda:self._select_page(self._current_page+1))
        self.page_label=QLabel("0 / 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setMinimumWidth(65)
        self.zoom_combo=SoftComboBox()
        for z in (50,75,100,125,150,200,250,300):
            self.zoom_combo.addItem(f"{z}%",z/100)
        self.zoom_combo.setCurrentIndex(2)
        self.zoom_combo.currentIndexChanged.connect(self._on_zoom_change)
        for w in (self.prev_button,self.page_label,self.next_button): bar.addWidget(w)
        bar.addStretch()
        bar.addWidget(QLabel("表示倍率"))
        bar.addWidget(self.zoom_combo)
        bar.addSpacing(10)
        bar.addWidget(QLabel("文字"))
        self.font_combo = SoftComboBox()
        self.font_combo.setToolTip("操作文字の太さを比較して選べます")
        for key, title in PRESETS.items():
            self.font_combo.addItem(title, key)
        self.font_combo.setCurrentIndex(list(PRESETS).index(self._font_preset))
        self.font_combo.currentIndexChanged.connect(self._on_font_choice)
        bar.addWidget(self.font_combo)
        self.font_source = QLabel("")
        self.font_source.setStyleSheet("color:#726A95;")
        bar.addWidget(self.font_source)
        layout.addLayout(bar)

        self.splitter=QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        left=QFrame()
        left.setObjectName("panel")
        v=QVBoxLayout(left)
        v.setContentsMargins(12,16,12,16)
        v.addWidget(QLabel("ページ一覧"))
        self.page_list=QListWidget()
        self.page_list.setIconSize(QSize(86,105))
        self.page_list.setSpacing(2)
        self.page_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.page_list.currentRowChanged.connect(self._select_page)
        self.page_list.verticalScrollBar().valueChanged.connect(self._schedule_thumbnails)
        v.addWidget(self.page_list)
        self.splitter.addWidget(left)
        right=QFrame()
        right.setObjectName("panel")
        v=QVBoxLayout(right)
        v.setContentsMargins(6,6,6,6)
        self.viewer=PdfViewer()
        self.viewer.region_requested.connect(self._request_visible_region)
        v.addWidget(self.viewer)
        self.splitter.addWidget(right)
        self.splitter.setSizes([190,920])
        self.splitter.setStretchFactor(1,1)
        layout.addWidget(self.splitter,1)
        self.statusBar().showMessage("起動準備中…")
        self._thumb_timer=QTimer(self)
        self._thumb_timer.setSingleShot(True)
        self._thumb_timer.setInterval(160)
        self._thumb_timer.timeout.connect(self._queue_visible_thumbnails)
        self._update_controls()

    def _on_font_choice(self, index: int):
        preset = self.font_combo.itemData(index)
        if preset in PRESETS:
            self._apply_font_preset(preset)

    def _apply_font_preset(self, preset: str, save: bool = True):
        self._font_preset = preset
        base_font = font_for_preset(preset)
        QApplication.instance().setFont(base_font)
        self.setFont(base_font)
        # Keep the application name prominent; compare the actual controls,
        # not only a preview sample.
        heading = QFont(base_font)
        heading.setPointSize(16)
        heading.setWeight(QFont.Weight.Bold)
        self.title_label.setFont(heading)
        source = font_status()
        if source["embedded"]:
            self.font_source.setText("書体：Zen Maru")
            self.font_source.setToolTip("アプリ専用フォントを読込済み。PCへのインストールは不要です。")
        else:
            self.font_source.setText("書体：代替")
            self.font_source.setToolTip(
                "フォント未配置：scripts/install_fonts.py を1回実行して再起動してください。"
            )
        if save:
            QSettings("pdf-works", "desktop").setValue("text_weight", preset)

    def _start_worker(self):
        try:
            self._bridge.start()
            self.statusBar().showMessage("準備完了。PDFを開いてください。")
        except Exception as exc: self._on_worker_failed(str(exc))

    def _choose_pdf(self):
        path,_=QFileDialog.getOpenFileName(self,"PDFを開く","","PDF files (*.pdf)")
        if path: self.open_pdf(path)

    def open_pdf(self,path:str):
        if not Path(path).is_file():
            self.statusBar().showMessage("指定ファイルが見つかりません。")
            return
        self._generation+=1
        self._pdf_path=path
        self._sizes=[]
        self._latest_image_req=None
        self._thumb_ready.clear()
        self._pending_thumbs.clear()
        self._thumb_queue.clear()
        self.page_list.blockSignals(True)
        self.page_list.clear()
        self.page_list.blockSignals(False)
        self.viewer.reset_document()
        self.filename.setText(Path(path).name)
        self.size_label.setText("")
        self.statusBar().showMessage("PDFを読み込み中…")
        self._bridge.send("open",path=path,generation=self._generation)

    def _on_worker_reply(self,response:dict):
        if response.get("generation")!=self._generation: return
        op=response.get("op")
        if response.get("status")!="ok":
            if op=="open":
                self.statusBar().showMessage("PDFを開けませんでした。")
                QMessageBox.warning(self,"PDF読み込みエラー",response.get("message","不明なエラー"))
            elif op=="thumb":
                self._pending_thumbs.discard(response.get("page"))
                self._send_next_thumbnail()
            else: self.statusBar().showMessage("PDF描画に失敗しました。")
            return
        if op=="open":
            file_bytes=response.get("file_bytes")
            if type(file_bytes) is int and file_bytes >= 0:
                self.size_label.setText(format_file_size(file_bytes))
                self.size_label.setToolTip(
                    f"元PDFの実際のファイル容量：{file_bytes:,} bytes"
                )
            self._sizes=[tuple(p) for p in response["sizes"]]
            self.page_list.blockSignals(True)
            for i in range(len(self._sizes)):
                self.page_list.addItem(QListWidgetItem(f"{i+1} ページ"))
            self.page_list.blockSignals(False)
            if self._sizes:
                self._select_page(0)
                self._schedule_thumbnails()
            self.statusBar().showMessage(f"{len(self._sizes)}ページを読み込みました。閲覧専用alpha版です。")
        elif op=="render":
            if response["id"]!=self._latest_image_req or response["page"]!=self._current_page: return
            pic=response["image"]
            self.viewer.show_image(rgb_to_pixmap(pic),pic["x"],pic["y"],pic["scale"])
        elif op=="thumb":
            self._pending_thumbs.discard(response["page"])
            idx=response["page"]
            if idx not in self._thumb_ready and idx<self.page_list.count():
                item=self.page_list.item(idx)
                item.setIcon(QIcon(rgb_to_pixmap(response["image"])))
                item.setSizeHint(QSize(120,119))
                self._thumb_ready.add(idx)
            self._send_next_thumbnail()

    def _on_worker_failed(self,message):
        self.statusBar().showMessage("PDF処理が停止しました。アプリを再起動してください。")
        QMessageBox.critical(self,"PDF処理エラー",message)

    def _select_page(self,index:int):
        if not 0<=index<len(self._sizes): return
        self._current_page=index
        self.page_list.blockSignals(True)
        self.page_list.setCurrentRow(index)
        self.page_list.blockSignals(False)
        width,height=self._sizes[index]
        self.viewer.set_page(width,height)
        self.page_label.setText(f"{index+1} / {len(self._sizes)}")
        self._update_controls()
        self._schedule_thumbnails()

    def _update_controls(self):
        self.prev_button.setEnabled(bool(self._sizes) and self._current_page>0)
        self.next_button.setEnabled(bool(self._sizes) and self._current_page+1<len(self._sizes))

    def _on_zoom_change(self,index:int):
        self.viewer.set_zoom(float(self.zoom_combo.itemData(index)))

    def _request_visible_region(self,region:tuple,scale:float):
        if not self._sizes: return
        rid=self._bridge.send("render",generation=self._generation,
            page=self._current_page,clip=region,scale=scale)
        if rid is not None: self._latest_image_req=rid

    def _schedule_thumbnails(self,*args):
        if self._sizes: self._thumb_timer.start()

    def _queue_visible_thumbnails(self):
        if not self._sizes: return
        top=self.page_list.indexAt(self.page_list.viewport().rect().topLeft()).row()
        bottom=self.page_list.indexAt(self.page_list.viewport().rect().bottomLeft()).row()
        if top<0: top=0
        if bottom<0: bottom=min(top+5,len(self._sizes)-1)
        for i in range(max(0,top-1),min(len(self._sizes),bottom+2)):
            if i not in self._thumb_ready and i not in self._pending_thumbs and i not in self._thumb_queue:
                self._thumb_queue.append(i)
        self._send_next_thumbnail()

    def _send_next_thumbnail(self):
        if self._pending_thumbs or not self._thumb_queue: return
        page=self._thumb_queue.popleft()
        rid=self._bridge.send("thumb",generation=self._generation,page=page)
        if rid is not None: self._pending_thumbs.add(page)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.width()<850 and self.splitter.sizes()[0]>145:
            self.splitter.setSizes([140,max(400,self.width()-200)])
        self._schedule_thumbnails()

    def closeEvent(self,event):
        self._bridge.close()
        event.accept()
