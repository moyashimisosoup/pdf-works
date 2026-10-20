"""Non-destructive page editor on top of the alpha viewer."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QListWidgetItem)
from .main_window import MainWindow
from .roi_gallery import CropGallery
from ..core.page_edit import EditSession
from ..core.page_extract import selected_page_specs


class EditWindow(MainWindow):
    def __init__(self):
        self._session: EditSession | None = None
        self._source_sizes: list[tuple[float, float]] = []
        self._edit_epoch = 0
        self._saving = False
        self._roi_exporting = False
        self._sheet_exporting = False
        self._page_exporting = False
        self._page_export_request = None
        self._page_export_operation = None
        self._sheet_request = None
        self._roi_request = None
        self._roi_sources_pending = []
        self._gallery_files = []
        self._gallery_sources = []
        self._gallery_order = []
        self._gallery_excluded = set()
        self._gallery = None
        self._gallery_serial = 0
        self._list_navigation = False
        self._save_request = None
        self._saved_snapshot: list[tuple[int, int]] | None = None
        super().__init__()
        self.setWindowTitle("pdf-works | Page editor beta")

    def _build_ui(self):
        super()._build_ui()
        # ExtendedSelection retains Qt's native Ctrl/Shift mouse and key behavior.
        self.page_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.page_list.currentRowChanged.disconnect(self._select_page)
        self.page_list.currentRowChanged.connect(self._on_page_current_changed)
        self.page_list.itemSelectionChanged.connect(self._on_page_selection_changed)
        self.selection_label = QLabel("選択 0 ページ")
        self.selection_label.setWordWrap(False)
        self.selection_label.setStyleSheet("color:#726A95;")
        self.page_list.parentWidget().layout().insertWidget(1, self.selection_label)
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
        self._setup_page_export_tools()
        self._setup_keyboard_shortcuts()
        self._update_controls()

    def _setup_page_export_tools(self):
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.extract_button = QPushButton("選択を抽出")
        self.extract_button.setToolTip(
            "選択したページだけを編集後の順序で別のPDFに保存します"
        )
        self.extract_button.clicked.connect(self._extract_selected)
        self.split_button = QPushButton("1ページずつ分割")
        self.split_button.setToolTip(
            "選択した各ページを個別PDFに保存します。元PDFは変更されません"
        )
        self.split_button.clicked.connect(self._split_selected)
        for button in (self.extract_button, self.split_button):
            button.setMinimumWidth(button.sizeHint().width() + 16)
            actions.addWidget(button)
        self.export_info = QLabel("選択ページを別名保存")
        self.export_info.setWordWrap(False)
        self.export_info.setStyleSheet("color: #726A95;")
        actions.addWidget(self.export_info)
        actions.addStretch(1)
        self.centralWidget().layout().insertLayout(4, actions)

    def _selected_specs(self):
        if self._session is None:
            return []
        rows = self._selected_rows()
        if not rows:
            return []
        return selected_page_specs(self._session.snapshot(), rows)

    def _page_output_busy(self):
        return (self._saving or self._roi_exporting
                or self._sheet_exporting or self._page_exporting)

    def _extract_selected(self):
        if self._session is None or not self._pdf_path or self._page_output_busy():
            return
        pages = self._selected_specs()
        if not pages:
            return
        source = Path(self._pdf_path)
        suggestion = source.with_name(source.stem + "_selected.pdf")
        name, _ = QFileDialog.getSaveFileName(
            self, "選択ページを抽出", str(suggestion), "PDF (*.pdf)",
        )
        if not name:
            return
        target = Path(name)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        if target.exists() or target.is_symlink() or target.resolve() == source.resolve():
            QMessageBox.warning(
                self, "保存先を確認",
                "元PDFや既存ファイルには上書きできません。",
            )
            return
        rid = self._bridge.send(
            "extract_selected", generation=self._generation,
            destination=str(target), pages=pages,
        )
        if rid is None:
            QMessageBox.warning(self, "処理中", "PDFワーカーが混雑しています。")
            return
        self._page_exporting = True
        self._page_export_operation = "extract_selected"
        self._page_export_request = rid
        self._update_controls()
        self.statusBar().showMessage(f"{len(pages)}ページを抽出中…")

    def _split_selected(self):
        if self._session is None or not self._pdf_path or self._page_output_busy():
            return
        pages = self._selected_specs()
        if not pages:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "分割PDFの保存先フォルダ",
        )
        if not folder:
            return
        answer = QMessageBox.question(
            self, "PDFを分割",
            f"選択中の{len(pages)}ページを、各1ページの別PDFに保存しますか？"
            "（元PDFは変更されません）",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        prefix = Path(self._pdf_path).stem[:48].strip(" .") + "_page"
        rid = self._bridge.send(
            "split_selected", generation=self._generation,
            destination_dir=folder, pages=pages, prefix=prefix,
        )
        if rid is None:
            QMessageBox.warning(self, "処理中", "PDFワーカーが混雑しています。")
            return
        self._page_exporting = True
        self._page_export_operation = "split_selected"
        self._page_export_request = rid
        self._update_controls()
        self.statusBar().showMessage(f"{len(pages)}ページを分割中…")

    def _setup_keyboard_shortcuts(self):
        self._shortcuts = []
        for sequence, parent, slot, context in (
            ("Ctrl+Shift+A", self.page_list, self.page_list.clearSelection,
             Qt.ShortcutContext.WidgetWithChildrenShortcut),
            ("Delete", self.page_list, lambda: self._edit(("delete",)),
             Qt.ShortcutContext.WidgetWithChildrenShortcut),
            ("Ctrl+Z", self, lambda: self._edit(("undo",)),
             Qt.ShortcutContext.WindowShortcut),
            ("Ctrl+O", self, self._choose_pdf, Qt.ShortcutContext.WindowShortcut),
            ("Ctrl+Shift+S", self, self._save_as, Qt.ShortcutContext.WindowShortcut),
        ):
            shortcut = QShortcut(QKeySequence(sequence), parent)
            shortcut.setContext(context)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

    def _selected_rows(self):
        return sorted(self.page_list.row(item)
                      for item in self.page_list.selectedItems())

    def _on_page_current_changed(self, index):
        if index < 0:
            return
        self._list_navigation = True
        try:
            self._select_page(index)
        finally:
            self._list_navigation = False

    def _on_page_selection_changed(self):
        self._update_controls()

    def _select_page(self, index):
        if not 0 <= index < len(self._sizes):
            return
        if not self._list_navigation:
            # Explicit page navigation selects one page; Ctrl/Shift selection
            # from the list keeps the other selected pages intact.
            self.page_list.blockSignals(True)
            self.page_list.setCurrentRow(
                index, QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )
            self.page_list.blockSignals(False)
        self._current_page = index
        width, height = self._sizes[index]
        self.viewer.set_page(width, height)
        self.page_label.setText(f"{index+1} / {len(self._sizes)}")
        self._update_controls()
        self._schedule_thumbnails()

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
        self.gallery_button = QPushButton("一覧表示")
        self.gallery_button.setToolTip("前回書き出した切り出し画像を一覧で開きます")
        self.gallery_button.clicked.connect(self._show_roi_gallery)
        for button in (self.roi_toggle, self.roi_clear, self.roi_export,
                       self.gallery_button):
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
                or self._saving or self._roi_exporting or self._sheet_exporting
                or self._page_exporting):
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
        self._roi_sources_pending = [p.source_index for p in self._session.pages]
        self._roi_exporting = True
        self._update_controls()
        self.statusBar().showMessage("PNGを出力中…")

    def _sheet_entries(self):
        ids = [uid for uid in self._gallery_order
               if uid not in self._gallery_excluded]
        return ([self._gallery_files[uid] for uid in ids],
                [self._gallery_sources[uid] for uid in ids])

    def _on_gallery_layout_changed(self, order, excluded):
        self._gallery_order = list(order)
        self._gallery_excluded = set(excluded)

    def _export_sheet(self):
        if (not self._gallery_files or not self._gallery_sources
                or self._saving or self._roi_exporting or self._sheet_exporting
                or self._page_exporting):
            return
        images, sources = self._sheet_entries()
        if not images:
            QMessageBox.information(
                self, "一覧PDF", "少なくとも1件を復元してください。"
            )
            return
        src = Path(self._pdf_path) if self._pdf_path else None
        suggested = str(src.with_name(src.stem + "_roi_sheet.pdf")) if src else "roi_sheet.pdf"
        name, _ = QFileDialog.getSaveFileName(
            self, "A4一覧PDFの保存", suggested, "PDF (*.pdf)"
        )
        if not name:
            return
        destination = Path(name)
        if destination.suffix.lower() != ".pdf":
            destination = destination.with_suffix(".pdf")
        if destination.exists() or destination.is_symlink() or (
            src is not None and destination.resolve() == src.resolve()
        ):
            QMessageBox.warning(
                self, "保存先を確認", "元PDFや既存ファイルには上書きできません。"
            )
            return
        request = self._bridge.send(
            "roi_sheet_export", generation=self._generation,
            destination=str(destination),
            files=images, sources=sources,
        )
        if request is None:
            QMessageBox.warning(self, "処理中", "PDFワーカーが混雑しています。")
            return
        self._sheet_request = request
        self._sheet_exporting = True
        self._update_controls()
        self.statusBar().showMessage("A4一覧PDFを作成中…")

    def _show_roi_gallery(self):
        if not self._gallery_files or len(self._gallery_files) != len(self._gallery_sources):
            return
        if self._gallery is not None:
            self._gallery.show()
            self._gallery.raise_()
            self._gallery.activateWindow()
            return
        gallery = CropGallery(
            self._gallery_files, self._gallery_sources, self,
            order=self._gallery_order, excluded=self._gallery_excluded,
        )
        self._gallery = gallery
        self._gallery_serial += 1
        serial = self._gallery_serial
        gallery.source_requested.connect(self._jump_to_source)
        gallery.pdf_requested.connect(self._export_sheet)
        gallery.layout_changed.connect(self._on_gallery_layout_changed)
        gallery.destroyed.connect(
            lambda *_: self._gallery_closed(serial)
        )
        gallery.show()

    def _gallery_closed(self, serial):
        if serial == self._gallery_serial:
            self._gallery = None

    def _jump_to_source(self, source_index):
        if self._session is None:
            return
        for index, page in enumerate(self._session.pages):
            if page.source_index == source_index:
                self._select_page(index)
                self.showNormal()
                self.raise_()
                self.activateWindow()
                return
        self.statusBar().showMessage("対象ページは現在の編集結果から削除されています。")

    def _dirty(self):
        return self._session is not None and self._session.snapshot() != self._saved_snapshot

    def open_pdf(self, path):
        if self._page_output_busy():
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
        self._gallery_files = []
        self._gallery_sources = []
        self._gallery_order = []
        self._gallery_excluded = set()
        if self._gallery is not None:
            self._gallery.close()
        self._edit_epoch += 1
        super().open_pdf(path)
        self.roi_toggle.setChecked(False)
        self._update_controls()

    def _on_worker_reply(self, response):
        if response.get("generation") != self._generation:
            return
        op = response.get("op")
        if op in ("extract_selected", "split_selected"):
            if (response.get("id") != self._page_export_request
                    or op != self._page_export_operation):
                return
            self._page_exporting = False
            self._page_export_request = None
            self._page_export_operation = None
            if response.get("status") == "ok":
                done = response.get("count", 0)
                result = ("抽出PDFを保存しました" if op == "extract_selected"
                          else "分割PDFを保存しました")
                self.statusBar().showMessage(f"{result}（{done}件）。")
            else:
                QMessageBox.warning(
                    self, "PDFを書き出せませんでした",
                    response.get("message", "原因不明のエラー"),
                )
            self._update_controls()
            return
        if op == "roi_sheet_export":
            if response.get("id") != self._sheet_request:
                return
            self._sheet_request = None
            self._sheet_exporting = False
            if response.get("status") == "ok":
                self.statusBar().showMessage(
                    f"A4一覧PDFを保存しました（{response['count']}ページ）。"
                )
            else:
                QMessageBox.warning(
                    self, "一覧PDFを保存できませんでした",
                    response.get("message", "原因不明のエラー"),
                )
            self._update_controls()
            return
        if op == "roi_export":
            if response.get("id") != self._roi_request:
                return
            self._roi_request = None
            self._roi_exporting = False
            if response.get("status") == "ok":
                files = response.get("files", [])
                if len(files) == len(self._roi_sources_pending):
                    if self._gallery is not None:
                        self._gallery.close()
                        self._gallery = None
                    self._gallery_files = list(files)
                    self._gallery_sources = list(self._roi_sources_pending)
                    self._gallery_order = list(range(len(files)))
                    self._gallery_excluded = set()
                self.statusBar().showMessage(
                    f"{response['count']}ページ分のPNGを出力しました。"
                )
            else:
                QMessageBox.warning(
                    self, "PNGを出力できませんでした",
                    response.get("message", "原因不明のエラー"),
                )
            self._roi_sources_pending = []
            self._update_controls()
            if response.get("status") == "ok" and self._gallery_files:
                self._show_roi_gallery()
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

    def _refresh_pages(self, selected, selected_sources=None):
        if self._session is None:
            return
        source_set = set(selected_sources or ())
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
        selected = max(0, min(selected, len(self._sizes) - 1))
        self.page_list.setCurrentRow(
            selected, QItemSelectionModel.SelectionFlag.NoUpdate
        )
        retained = 0
        if source_set:
            for index, page in enumerate(self._session.pages):
                if page.source_index in source_set:
                    self.page_list.item(index).setSelected(True)
                    retained += 1
        if not retained:
            self.page_list.item(selected).setSelected(True)
        self.page_list.blockSignals(False)
        self._list_navigation = True
        try:
            self._select_page(selected)
        finally:
            self._list_navigation = False
        self._update_controls()

    def _edit(self, action):
        if self._session is None or self._page_output_busy():
            return
        operation = action[0]
        rows = self._selected_rows()
        idx = self._current_page
        before = self._session.pages
        selected_sources = {before[row].source_index for row in rows
                            if 0 <= row < len(before)}
        try:
            if operation == "rotate":
                if not rows:
                    return
                self._session.rotate_many(rows, action[1])
            elif operation == "delete":
                if not rows:
                    return
                if len(rows) >= len(before):
                    QMessageBox.information(
                        self, "削除できません",
                        "すべてのページは削除できません。1ページ以上残してください。"
                    )
                    return
                if QMessageBox.question(
                    self, "ページ削除",
                    f"選択中の{len(rows)}ページを削除しますか？（元PDFは変わりません）",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                ) != QMessageBox.StandardButton.Yes:
                    return
                self._session.delete_many(rows)
                selected_sources.clear()
                idx = min(rows[0], len(self._session.pages) - 1)
            elif operation == "move":
                if len(rows) != 1:
                    return
                idx = rows[0] + action[1]
                self._session.move(rows[0], idx)
            elif operation == "undo":
                if not self._session.undo():
                    return
                selected_sources.clear()
            else:
                return
            self._refresh_pages(idx, selected_sources)
        except (ValueError, IndexError) as exc:
            QMessageBox.information(self, "編集できません", str(exc))

    def _update_controls(self):
        super()._update_controls()
        if not hasattr(self, "_edit_buttons"):
            return
        ready = self._session is not None and not self._page_output_busy()
        rows = self._selected_rows() if ready else []
        total = len(self._session.pages) if self._session else 0
        self.selection_label.setText(f"選択 {len(rows)}/{total} ページ")
        index = rows[0] if len(rows) == 1 else self._current_page
        for key, button in self._edit_buttons.items():
            active = ready and bool(rows)
            if key == "delete":
                active = active and len(rows) < total
            if key == "up":
                active = active and len(rows) == 1 and index > 0
            if key == "down":
                active = active and len(rows) == 1 and index < total - 1
            if key == "undo":
                active = ready and self._session.can_undo
            button.setEnabled(active)
        self.save_button.setEnabled(ready)
        self.extract_button.setEnabled(ready and bool(rows))
        self.split_button.setEnabled(ready and bool(rows))
        self.open_button.setEnabled(ready or self._session is None)
        if hasattr(self, "roi_toggle"):
            self.roi_toggle.setEnabled(ready)
            self.roi_clear.setEnabled(ready and self.viewer.roi is not None)
            self.roi_export.setEnabled(ready and self.viewer.roi is not None)
            self.gallery_button.setEnabled(bool(self._gallery_files))

    def _save_as(self):
        if (self._session is None or self._page_output_busy()
                or not self._pdf_path):
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
        if self._page_output_busy():
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
