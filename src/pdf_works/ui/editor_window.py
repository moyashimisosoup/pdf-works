"""Non-destructive page editor on top of the alpha viewer."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QListWidgetItem
from .main_window import MainWindow
from ..core.page_edit import EditSession


class EditWindow(MainWindow):
    def __init__(self):
        self._session: EditSession | None = None
        self._source_sizes: list[tuple[float, float]] = []
        self._edit_epoch = 0
        self._saving = False
        self._roi_exporting = False
        self._roi_request = None
        self._save_request = None
        self._saved_snapshot: list[tuple[int, int]] | None = None
        super().__init__()
        self.setWindowTitle("pdf-works | Page editor beta")

    def _build_ui(self):
        super()._build_ui()
        tools = QHBoxLayout()
        tools.setSpacing(6)
        self._edit_buttons = {}
        for key, label, args in (
            ("left", "↶ 90°", ("rotate", -90)),
            ("right", "↷ 90°", ("rotate", 90)),
            ("delete", "削除", ("delete",)),
            ("up", "上へ", ("move", -1)),
            ("down", "下へ", ("move", 1)),
            ("undo", "元に戻す", ("undo",)),
        ):
            button = QPushButton(label)
            if key == "delete":
                button.setObjectName("danger")
            button.setMinimumWidth(button.sizeHint().width() + 12)
            button.clicked.connect(lambda checked=False, a=args: self._edit(a))
            self._edit_buttons[key] = button
            tools.addWidget(button)
        tools.addStretch(1)
        self.centralWidget().layout().insertLayout(2, tools)
        self.save_button = QPushButton("別名保存")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self._save_as)
        self.centralWidget().layout().itemAt(0).layout().insertWidget(2, self.save_button)
        self._setup_roi_tools()
        self._update_controls()

    def _setup_roi_tools(self):
        roi_tools = QHBoxLayout()
        roi_tools.setSpacing(8)
        self.roi_toggle = QPushButton("範囲を選択")
        self.roi_toggle.setCheckable(True)
        self.roi_toggle.setToolTip("選択中はPDFをドラッグして範囲を指定します")
        self.roi_toggle.toggled.connect(self.viewer.enable_roi_selection)
        self.roi_clear = QPushButton("範囲解除")
        self.roi_clear.clicked.connect(self.viewer.clear_roi)
        self.roi_export = QPushButton("PNG出力")
        self.roi_export.setObjectName("primary")
        self.roi_export.setToolTip("同じ相対位置を現在の全ページからPNG出力")
        self.roi_export.clicked.connect(self._export_roi)
        for button in (self.roi_toggle, self.roi_clear, self.roi_export):
            button.setMinimumWidth(button.sizeHint().width() + 14)
            roi_tools.addWidget(button)
        self.roi_info = QLabel("範囲未指定")
        self.roi_info.setWordWrap(False)
        self.roi_info.setStyleSheet("color: #726A95;")
        roi_tools.addWidget(self.roi_info)
        roi_tools.addStretch(1)
        self.centralWidget().layout().insertLayout(3, roi_tools)
        self.viewer.roi_changed.connect(self._on_roi_changed)

    def _on_roi_changed(self, normalized):
        if not hasattr(self, "roi_info"):
            return
        if len(normalized) == 4:
            left, top, right, bottom = normalized
            self.roi_info.setText(
                f"指定範囲 {100*(right-left):.1f}% × {100*(bottom-top):.1f}%"
            )
        else:
            self.roi_info.setText("範囲未指定")
        self._update_controls()

    def _export_roi(self):
        if (self._session is None or not self._pdf_path
                or self._saving or self._roi_exporting):
            return
        roi = self.viewer.roi
        if roi is None:
            QMessageBox.information(self, "切り出し", "先にPDF上で範囲を指定してください。")
            return
        folder = QFileDialog.getExistingDirectory(self, "PNGの出力先フォルダ")
        if not folder:
            return
        rid = self._bridge.send(
            "roi_export", generation=self._generation, destination_dir=folder,
            roi=roi, pages=self._session.snapshot(), dpi=200,
        )
        if rid is None:
            QMessageBox.warning(self, "出力できません", "処理が混雑しています。少し待ってください。")
            return
        self._roi_request = rid
        self._roi_exporting = True
        self._update_controls()
        self.statusBar().showMessage("PNGを出力中…")

    def _dirty(self):
        return self._session is not None and self._session.snapshot() != self._saved_snapshot

    def open_pdf(self, path):
        if self._saving or self._roi_exporting:
            QMessageBox.information(self, "処理中", "書き出しが終わるまでお待ちください。")
            return
        if self._dirty() and QMessageBox.question(
            self, "未保存の編集", "編集中の変更を破棄して別のPDFを開きますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        self._session = None
        self._source_sizes = []
        self._saved_snapshot = None
        self._edit_epoch += 1
        super().open_pdf(path)
        self.roi_toggle.setChecked(False)
        self._update_controls()

    def _on_worker_reply(self, response):
        if response.get("generation") != self._generation:
            return
        op = response.get("op")
        if op == "roi_export":
            if response.get("id") != self._roi_request:
                return
            self._roi_request = None
            self._roi_exporting = False
            if response.get("status") == "ok":
                self.statusBar().showMessage(
                    f"{response['count']}ページ分のPNGを出力しました。"
                )
            else:
                QMessageBox.warning(
                    self, "PNGを出力できませんでした",
                    response.get("message", "原因不明のエラー"),
                )
            self._update_controls()
            return
        if op == "export":
            if response.get("id") != self._save_request:
                return
            self._saving = False
            self._save_request = None
            if response.get("status") == "ok":
                self._saved_snapshot = self._session.snapshot() if self._session else None
                self.statusBar().showMessage("別名保存しました: " + response["destination"])
            else:
                QMessageBox.warning(self, "保存できませんでした", response.get("message", "原因不明"))
            self._update_controls()
            return
        if op == "open" and response.get("status") == "ok":
            self._source_sizes = [tuple(x) for x in response["sizes"]]
            self._session = EditSession(len(self._source_sizes))
            self._saved_snapshot = self._session.snapshot()
        if op in ("thumb", "render"):
            if response.get("epoch") != self._edit_epoch:
                return
            response = {**response, "page": response.get("slot", response.get("page"))}
        super()._on_worker_reply(response)
        if op == "open":
            self._update_controls()

    def _request_visible_region(self, region, scale):
        if self._session is None or not self._sizes:
            return
        page = self._session.pages[self._current_page]
        rid = self._bridge.send("render", generation=self._generation,
            page=page.source_index, slot=self._current_page,
            rotation=page.rotation_delta, epoch=self._edit_epoch,
            clip=region, scale=scale)
        if rid is not None:
            self._latest_image_req = rid

    def _send_next_thumbnail(self):
        if self._session is None or self._pending_thumbs or not self._thumb_queue:
            return
        slot = self._thumb_queue.popleft()
        page = self._session.pages[slot]
        rid = self._bridge.send("thumb", generation=self._generation,
            page=page.source_index, slot=slot,
            rotation=page.rotation_delta, epoch=self._edit_epoch)
        if rid is not None:
            self._pending_thumbs.add(slot)

    def _refresh_pages(self, selected):
        if self._session is None:
            return
        self._edit_epoch += 1
        self._latest_image_req = None
        self._thumb_ready.clear()
        self._pending_thumbs.clear()
        self._thumb_queue.clear()
        self._sizes = []
        self.page_list.blockSignals(True)
        self.page_list.clear()
        for p in self._session.pages:
            w, h = self._source_sizes[p.source_index]
            if p.rotation_delta in (90, 270):
                w, h = h, w
            self._sizes.append((w, h))
            mark = f" ↻{p.rotation_delta}°" if p.rotation_delta else ""
            self.page_list.addItem(QListWidgetItem(f"元{p.source_index+1}{mark}"))
        self.page_list.blockSignals(False)
        self._select_page(max(0, min(selected, len(self._sizes)-1)))
        self._update_controls()

    def _edit(self, action):
        if self._session is None or self._saving:
            return
        idx = self._current_page
        operation = action[0]
        try:
            if operation == "rotate":
                self._session.rotate(idx, action[1])
            elif operation == "delete":
                if QMessageBox.question(self, "ページ削除", "このページを削除しますか？（元PDFは変更されません）",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                ) != QMessageBox.StandardButton.Yes:
                    return
                self._session.delete(idx)
            elif operation == "move":
                idx = idx + action[1]
                self._session.move(self._current_page, idx)
            elif operation == "undo":
                if not self._session.undo():
                    return
            self._refresh_pages(idx)
        except (ValueError, IndexError) as exc:
            QMessageBox.information(self, "編集できません", str(exc))

    def _update_controls(self):
        super()._update_controls()
        if not hasattr(self, "_edit_buttons"):
            return
        ready = self._session is not None and not self._saving and not self._roi_exporting
        idx = self._current_page
        for key, button in self._edit_buttons.items():
            active = ready
            if key == "delete": active = ready and len(self._session.pages) > 1
            if key == "up": active = ready and idx > 0
            if key == "down": active = ready and idx < len(self._session.pages)-1
            if key == "undo": active = ready and self._session.can_undo
            button.setEnabled(active)
        self.save_button.setEnabled(ready)
        self.open_button.setEnabled(not self._saving and not self._roi_exporting)
        if hasattr(self, "roi_toggle"):
            self.roi_toggle.setEnabled(ready)
            self.roi_clear.setEnabled(ready and self.viewer.roi is not None)
            self.roi_export.setEnabled(ready and self.viewer.roi is not None)

    def _save_as(self):
        if self._session is None or self._saving or self._roi_exporting or not self._pdf_path:
            return
        src = Path(self._pdf_path)
        proposal = str(src.with_name(src.stem + "_edited.pdf"))
        name, _ = QFileDialog.getSaveFileName(self, "別名保存", proposal, "PDF (*.pdf)")
        if not name:
            return
        target = Path(name)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        if target.resolve() == src.resolve() or target.exists():
            QMessageBox.warning(self, "保存先を確認", "元PDFや既存ファイルには上書きできません。別のファイル名を指定してください。")
            return
        pages = self._session.snapshot()
        rid = self._bridge.send("export", generation=self._generation,
            path=str(src), destination=str(target), pages=pages)
        if rid is None:
            QMessageBox.warning(self, "保存できません", "PDF処理が混雑しています。少し待って再試行してください。")
            return
        self._saving = True
        self._save_request = rid
        self._update_controls()
        self.statusBar().showMessage("別名PDFを保存しています…")

    def closeEvent(self, event):
        if self._saving or self._roi_exporting:
            QMessageBox.information(self, "処理中", "書き出し終了後に閉じてください。")
            event.ignore()
            return
        if self._dirty() and QMessageBox.question(
            self, "未保存の編集", "編集した内容が保存されていません。終了しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        super().closeEvent(event)
