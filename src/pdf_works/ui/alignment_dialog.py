"""Single-pair A/B overlay and PDF alignment dialog for scoring workflows.

Only A is adjustable. Preview and export PDF I/O run in a dedicated spawned
worker through PdfBridge. The UI never parses private school documents.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QSlider,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from ..core.alignment import placement
from ..workers.bridge import PdfBridge


class AlignmentDialog(QDialog):
    """Match one answer sheet A to one fixed reference B and export A only."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("重ね合わせ・縮尺合わせ | PDF Works")
        self.resize(1050, 770)
        self.setMinimumSize(740, 590)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._source: Path | None = None
        self._reference: Path | None = None
        self._details: dict | None = None
        self._images: dict[str, QImage] = {}
        self._preview_request: int | None = None
        self._export_request: int | None = None
        self._exporting = False
        self._bridge = PdfBridge(self)
        self._bridge.result_ready.connect(self._receive)
        self._bridge.worker_failed.connect(self._worker_failed)
        self._redraw_timer = QTimer(self)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(45)
        self._redraw_timer.timeout.connect(self._redraw)
        self._build()
        self._bridge.start()

    @staticmethod
    def _preview_label(message: str) -> QLabel:
        label = QLabel(message)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumSize(180, 270)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        label.setStyleSheet(
            "background:#FFFFFF;border:1px solid #D8D0D4;"
            "border-radius:10px;color:#726A95;"
        )
        return label

    @staticmethod
    def _file_card(title: str, button_title: str) -> tuple[QFrame, QLabel, QPushButton]:
        frame = QFrame()
        frame.setObjectName("panel")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(5)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight:600;")
        outer.addWidget(heading)
        line = QHBoxLayout()
        name = QLabel("PDFを選択")
        name.setStyleSheet("color:#726A95;")
        name.setMinimumWidth(90)
        name.setToolTip("元ファイルは変更しません")
        line.addWidget(name, 1)
        select = QPushButton(button_title)
        select.setMinimumWidth(118)
        line.addWidget(select)
        outer.addLayout(line)
        return frame, name, select

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 14, 15, 12)
        root.setSpacing(10)

        heading = QHBoxLayout()
        title = QLabel("縮尺合わせ")
        title.setStyleSheet("font-size:17px;font-weight:700;")
        heading.addWidget(title)
        hint = QLabel("Aの縮尺・位置をBに合わせて、調整済みAだけを新規PDFに保存")
        hint.setStyleSheet("color:#726A95;")
        heading.addWidget(hint, 1)
        root.addLayout(heading)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        a_card, self.a_filename, self.a_button = self._file_card(
            "A｜取り込み側（調整対象）", "Aを開く"
        )
        b_card, self.b_filename, self.b_button = self._file_card(
            "B｜見本（固定）", "Bを開く"
        )
        self.a_button.clicked.connect(lambda: self._choose("a"))
        self.b_button.clicked.connect(lambda: self._choose("b"))
        file_row.addWidget(a_card, 1)
        file_row.addWidget(b_card, 1)
        root.addLayout(file_row)

        display_row = QHBoxLayout()
        display_row.setSpacing(10)
        display_row.addWidget(QLabel("見比べ方"))
        self.mode = QComboBox()
        self.mode.addItems(("左右に並べる", "半透明で重ねる"))
        self.mode.setMinimumWidth(165)
        self.mode.currentIndexChanged.connect(self._change_mode)
        display_row.addWidget(self.mode)
        display_row.addSpacing(12)
        display_row.addWidget(QLabel("Aの不透明度"))
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(10, 90)
        self.opacity.setSingleStep(5)
        self.opacity.setPageStep(10)
        self.opacity.setValue(50)
        self.opacity.setMaximumWidth(165)
        self.opacity.valueChanged.connect(self._opacity_changed)
        display_row.addWidget(self.opacity)
        self.opacity_value = QLabel("50%")
        self.opacity_value.setMinimumWidth(38)
        display_row.addWidget(self.opacity_value)
        display_row.addStretch(1)
        self.page_info = QLabel("各PDFの1ページ目を比較")
        self.page_info.setStyleSheet("color:#726A95;")
        display_row.addWidget(self.page_info)
        root.addLayout(display_row)

        self.display = QStackedWidget()
        side = QWidget()
        two = QHBoxLayout(side)
        two.setContentsMargins(0, 0, 0, 0)
        two.setSpacing(10)
        a_box = QVBoxLayout()
        a_box.addWidget(QLabel("A：調整後の配置"))
        self.a_preview = self._preview_label("AとBのPDFを選択してください")
        a_box.addWidget(self.a_preview, 1)
        b_box = QVBoxLayout()
        b_box.addWidget(QLabel("B：固定された見本"))
        self.b_preview = self._preview_label("見本Bを選択してください")
        b_box.addWidget(self.b_preview, 1)
        two.addLayout(a_box, 1)
        two.addLayout(b_box, 1)
        self.display.addWidget(side)

        overlay = QWidget()
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.addWidget(QLabel("重ね合わせ：Bを固定し、Aだけを調整"))
        self.overlay_preview = self._preview_label("AとBのPDFを選択してください")
        overlay_layout.addWidget(self.overlay_preview, 1)
        self.display.addWidget(overlay)
        root.addWidget(self.display, 1)

        settings = QFrame()
        settings.setObjectName("panel")
        settings_row = QHBoxLayout(settings)
        settings_row.setContentsMargins(12, 9, 12, 9)
        settings_row.setSpacing(9)
        settings_row.addWidget(QLabel("Aの調整"))
        self.scale = QDoubleSpinBox()
        self.scale.setRange(30.0, 300.0)
        self.scale.setDecimals(1)
        self.scale.setSingleStep(0.1)
        self.scale.setSuffix("%")
        self.scale.setValue(100.0)
        self.scale.setToolTip("100%はAをBのページ内に収めた初期倍率。0.1%単位で変更")
        self.x_offset = QDoubleSpinBox()
        self.y_offset = QDoubleSpinBox()
        for spin, text in (
            (self.x_offset, "横"), (self.y_offset, "縦")
        ):
            spin.setRange(-100.0, 100.0)
            spin.setDecimals(1)
            spin.setSingleStep(0.5)
            spin.setSuffix(" mm")
            spin.setToolTip(f"Aの{text}方向への移動量（ミリメートル）")
        for name, control in (
            ("倍率", self.scale), ("X", self.x_offset), ("Y", self.y_offset)
        ):
            settings_row.addWidget(QLabel(name))
            control.setMinimumWidth(100)
            settings_row.addWidget(control)
            control.valueChanged.connect(self._schedule_redraw)
        self.reset_button = QPushButton("調整を戻す")
        self.reset_button.clicked.connect(self._reset)
        settings_row.addWidget(self.reset_button)
        settings_row.addStretch(1)
        root.addWidget(settings)

        # Only show this consent when A really contains interactive objects.
        # A bare AcroForm dictionary with zero widgets is not a reason to block.
        self.visual_warning = QLabel("")
        self.visual_warning.setWordWrap(True)
        self.visual_warning.setStyleSheet("color:#94602F;")
        self.visual_warning.hide()
        root.addWidget(self.visual_warning)
        self.visual_consent = QCheckBox(
            "入力欄・注釈などを表示内容として固定し、リンク・添付情報を省いた"
            "新しいPDFを作成する"
        )
        self.visual_consent.setToolTip(
            "Aの元PDFは変更しません。新しいPDFは印刷用の見た目を優先します。"
        )
        self.visual_consent.toggled.connect(lambda *_: self._controls())
        self.visual_consent.hide()
        root.addWidget(self.visual_consent)

        footer = QHBoxLayout()
        self.message = QLabel("AとBを選択してください。元ファイルは変更しません。")
        self.message.setStyleSheet("color:#726A95;")
        footer.addWidget(self.message, 1)
        self.save_button = QPushButton("調整済みAを別名保存")
        self.save_button.setObjectName("primary")
        self.save_button.setMinimumWidth(195)
        self.save_button.clicked.connect(self._save)
        self.close_button = QPushButton("閉じる")
        self.close_button.clicked.connect(self.close)
        footer.addWidget(self.save_button)
        footer.addWidget(self.close_button)
        root.addLayout(footer)

        self._change_mode()
        self._controls()

    def _controls(self):
        ready = bool(self._details and self._images)
        for button in (self.a_button, self.b_button):
            button.setEnabled(not self._exporting)
        for widget in (
            self.scale, self.x_offset, self.y_offset, self.reset_button,
            self.mode, self.opacity,
        ):
            widget.setEnabled(ready and not self._exporting)
        self.opacity.setEnabled(
            ready and not self._exporting and self.mode.currentIndex() == 1
        )
        issues = self._details.get("source_issues", []) if self._details else []
        signed = "signature" in issues
        needs_consent = bool(issues) and not signed
        self.visual_consent.setEnabled(ready and not self._exporting)
        self.save_button.setEnabled(
            ready and not self._exporting and not signed
            and (not needs_consent or self.visual_consent.isChecked())
        )

    def _choose(self, which: str):
        if self._exporting:
            return
        name, _ = QFileDialog.getOpenFileName(
            self, "取り込み側Aを選択" if which == "a" else "見本Bを選択",
            "", "PDF (*.pdf)",
        )
        if not name:
            return
        path = Path(name)
        if which == "a":
            self._source = path
            label = self.a_filename
        else:
            self._reference = path
            label = self.b_filename
        label.setText(path.name)
        label.setToolTip(str(path))
        self._details = None
        self._images = {}
        self.visual_consent.setChecked(False)
        self.visual_consent.hide()
        self.visual_warning.hide()
        self._controls()
        if self._source is not None and self._reference is not None:
            self._request_preview()

    def _request_preview(self):
        if self._exporting:
            return
        self.message.setText("プレビューを作成しています…")
        self.a_preview.setText("読み込み中…")
        self.b_preview.setText("読み込み中…")
        self.overlay_preview.setText("読み込み中…")
        rid = self._bridge.send(
            "align_preview", source=str(self._source),
            reference=str(self._reference),
        )
        if rid is None:
            self.message.setText("処理が混雑しています。もう一度ファイルを選択してください。")
        else:
            self._preview_request = rid

    @staticmethod
    def _to_qimage(data: dict) -> QImage:
        image = QImage(
            data["samples"], data["width"], data["height"],
            data["stride"], QImage.Format.Format_RGB888,
        ).copy()
        if image.isNull():
            raise ValueError("Cannot read preview bitmap")
        return image

    def _receive(self, reply: dict):
        op = reply.get("op")
        if op == "align_preview":
            if reply.get("id") != self._preview_request:
                return
            self._preview_request = None
            if reply.get("status") != "ok":
                self.message.setText("読み込みに失敗しました")
                QMessageBox.warning(
                    self, "PDFを比較できません", reply.get("message", "不明なエラー")
                )
                return
            self._details = {
                "source_size": tuple(reply["source_size"]),
                "reference_size": tuple(reply["reference_size"]),
                "source_pages": int(reply["source_pages"]),
                "reference_pages": int(reply["reference_pages"]),
                "source_issues": list(reply.get("source_issues", [])),
            }
            try:
                self._images = {
                    key: self._to_qimage(reply["images"][key])
                    for key in ("a", "b")
                }
            except ValueError:
                self._details = None
                self._images = {}
                self.message.setText("プレビュー画像を表示できません")
                return
            self.page_info.setText(
                f"A全{self._details['source_pages']}ページを出力 / "
                "表示比較は各1ページ目"
            )
            issues = self._details["source_issues"]
            self.visual_consent.setChecked(False)
            if "signature" in issues:
                self.visual_warning.setText(
                    "Aには電子署名が含まれています。比較表示はできますが、"
                    "署名の有効性を保護するため、この画面では書き出せません。"
                )
                self.visual_warning.show()
                self.visual_consent.hide()
                self.message.setText("電子署名付きAは比較のみ可能です")
            elif issues:
                self.visual_warning.setText(
                    "AのPDFにフォーム入力欄・注釈・リンク・添付ファイルの"
                    "いずれかが含まれています。比較は可能です。"
                    "別名出力では画面に見える内容を固定し、"
                    "リンク・添付・編集可能な入力欄は引き継ぎません。"
                )
                self.visual_warning.show()
                self.visual_consent.show()
                self.message.setText("表示内容の固定に同意すると別名保存できます")
            else:
                self.visual_warning.hide()
                self.visual_consent.hide()
                self.message.setText("倍率・位置を調整してAだけを保存できます")
            self._controls()
            self._redraw()
        elif op == "align_export":
            if reply.get("id") != self._export_request:
                return
            self._export_request = None
            self._exporting = False
            self._controls()
            if reply.get("status") == "ok":
                self.message.setText(
                    f"Aを{reply['pages']}ページ保存しました"
                )
                QMessageBox.information(
                    self, "保存完了",
                    f"調整したAを新しいPDFに保存しました。\n{reply['destination']}",
                )
            else:
                self.message.setText("保存できませんでした。元ファイルは変更していません。")
                QMessageBox.warning(
                    self, "保存できませんでした",
                    reply.get("message", "不明なエラー"),
                )

    def _worker_failed(self, message: str):
        self._exporting = False
        self._details = None
        self._controls()
        QMessageBox.warning(self, "PDF処理エラー", message)

    def _change_mode(self, *_):
        self.display.setCurrentIndex(self.mode.currentIndex())
        self._controls()
        self._schedule_redraw()

    def _opacity_changed(self, value: int):
        self.opacity_value.setText(f"{value}%")
        self._schedule_redraw()

    def _schedule_redraw(self, *_):
        if self._images:
            self._redraw_timer.start()

    def _reset(self):
        for control, value in (
            (self.scale, 100.0),
            (self.x_offset, 0.0),
            (self.y_offset, 0.0),
        ):
            control.setValue(value)
        self._schedule_redraw()

    @staticmethod
    def _fit(label: QLabel, bitmap: QImage):
        available = label.size() - QSize(14, 14)
        if available.width() < 10 or available.height() < 10:
            return
        pixmap = QPixmap.fromImage(bitmap)
        label.setPixmap(pixmap.scaled(
            available, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def _compose(self, *, opacity: float, background: bool) -> QImage:
        b = self._images["b"]
        a = self._images["a"]
        canvas = QImage(b.width(), b.height(), QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(QColor("#FFFFFF"))
        painter = QPainter(canvas)
        if background:
            painter.drawImage(0, 0, b)
        rect = placement(
            self._details["source_size"], self._details["reference_size"],
            self.scale.value(), self.x_offset.value(), self.y_offset.value(),
        )
        ref_width, ref_height = self._details["reference_size"]
        target = QRectF(
            rect[0] * b.width() / ref_width,
            rect[1] * b.height() / ref_height,
            (rect[2] - rect[0]) * b.width() / ref_width,
            (rect[3] - rect[1]) * b.height() / ref_height,
        )
        painter.setOpacity(opacity)
        painter.drawImage(target, a)
        painter.end()
        return canvas

    def _redraw(self):
        if not self._details or not self._images:
            return
        self._fit(self.a_preview, self._compose(opacity=1.0, background=False))
        self._fit(self.b_preview, self._images["b"])
        self._fit(
            self.overlay_preview,
            self._compose(opacity=self.opacity.value() / 100.0, background=True),
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_redraw_timer"):
            self._schedule_redraw()

    def _save(self):
        if not self._details or self._exporting:
            return
        issues = self._details.get("source_issues", [])
        if "signature" in issues or (issues and not self.visual_consent.isChecked()):
            return
        suggestion = str(self._source.with_name(self._source.stem + "_aligned.pdf"))
        name, _ = QFileDialog.getSaveFileName(
            self, "調整済みAを別名保存", suggestion, "PDF (*.pdf)",
        )
        if not name:
            return
        target = Path(name)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        if (target.resolve() in (self._source.resolve(), self._reference.resolve())
                or target.exists() or target.is_symlink()):
            QMessageBox.warning(
                self, "保存先を確認",
                "元ファイルA・Bや既存のファイルは上書きできません。",
            )
            return
        rid = self._bridge.send(
            "align_export", source=str(self._source),
            reference=str(self._reference),
            destination=str(target), percent=self.scale.value(),
            x_mm=self.x_offset.value(), y_mm=self.y_offset.value(),
            allow_visual_only=self.visual_consent.isChecked(),
        )
        if rid is None:
            QMessageBox.warning(self, "処理中", "PDF処理が混雑しています。")
            return
        self._export_request = rid
        self._exporting = True
        self._controls()
        self.message.setText("Aを新しいPDFに書き出しています…")

    def closeEvent(self, event):
        if self._exporting:
            QMessageBox.information(
                self, "処理中", "PDFの書き出しが終わってから閉じてください。"
            )
            event.ignore()
            return
        self._bridge.close()
        super().closeEvent(event)
