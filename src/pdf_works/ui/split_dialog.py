"""Compact page-group split configuration dialog, no PDF processing on GUI."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QLabel, QLineEdit, QSpinBox, QVBoxLayout, QWidget,
)

from ..core.page_partition import partition_page_specs


class SplitGroupsDialog(QDialog):
    def __init__(self, snapshot: list[tuple[int, int]], parent=None):
        super().__init__(parent)
        self._snapshot = list(snapshot)
        self.configuration = None
        self.setWindowTitle("分割条件")
        self.setMinimumWidth(370)
        self.resize(460, 230)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.mode = QComboBox(self)
        self.mode.addItem("指定ページ数ごと", "fixed")
        self.mode.addItem("指定位置で区切る", "boundaries")
        form.addRow("分割方法", self.mode)
        self.size = QSpinBox(self)
        self.size.setMinimum(1)
        self.size.setMaximum(max(1, len(snapshot) - 1))
        self.size.setValue(min(5, max(1, len(snapshot) - 1)))
        self.size.setSuffix(" ページ")
        form.addRow("1ファイル", self.size)
        self.boundaries = QLineEdit(self)
        self.boundaries.setPlaceholderText("例：3, 7（3ページ目と7ページ目の後）")
        self.boundaries.setText(str(max(1, len(snapshot) // 2)))
        form.addRow("区切り位置", self.boundaries)
        layout.addLayout(form)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("分割して保存")
        self.buttons.accepted.connect(self._accept_config)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.mode.currentIndexChanged.connect(self._refresh)
        self.size.valueChanged.connect(self._refresh)
        self.boundaries.textChanged.connect(self._refresh)
        self._refresh()

    def _current_config(self):
        mode = self.mode.currentData()
        if mode == "fixed":
            return {"mode": "fixed", "size": self.size.value(), "boundaries": None}
        raw = self.boundaries.text().strip().replace("、", ",").replace("，", ",")
        values = [value.strip() for value in raw.split(",")]
        if not values or any(not item.isascii() or not item.isdecimal() for item in values):
            raise ValueError("区切り位置をページ番号で入力してください（例：3, 7）")
        return {"mode": "boundaries", "size": None,
                "boundaries": [int(item) for item in values]}

    def _refresh(self, *_):
        fixed = self.mode.currentData() == "fixed"
        self.size.setEnabled(fixed)
        self.boundaries.setEnabled(not fixed)
        valid = False
        try:
            config = self._current_config()
            groups = partition_page_specs(self._snapshot, **config)
            if len(groups) < 2:
                raise ValueError("分割には2ファイル以上が必要です")
            sizes = [len(group) for group in groups]
            preview = " / ".join(map(str, sizes[:8]))
            if len(sizes) > 8:
                preview += " / …"
            self.info.setText(
                f"{len(self._snapshot)}ページ → {len(groups)}ファイル\n"
                f"各ファイルのページ数：{preview}\n"
                "元PDFは変更せず、出力先の既存ファイルも上書きしません。"
            )
            valid = True
        except (ValueError, TypeError) as exc:
            self.info.setText(str(exc))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)

    def _accept_config(self):
        self._refresh()
        if not self.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
            return
        self.configuration = self._current_config()
        self.accept()
