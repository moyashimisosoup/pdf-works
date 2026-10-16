# v5.0-beta Windows試験（開発ブランチ専用）

**対象**：`feature/native-page-edit-20261017`。mainの動作確認済みalphaとは別の未検証版です。

## 起動まで

既にGit clone済みの `pdf-works` ディレクトリから：

```powershell
git fetch origin
git switch feature/native-page-edit-20261017
.\.venv\Scripts\python.exe -m pip install -e ".[desktop,dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/generate_test_pdf.py tests/sample_40.pdf --pages 40
.\.venv\Scripts\python.exe -m pdf_works
```

## 手動で確認すること
1. 空画面表示・PDF読込・ページ送り・300%ズームが以前と同様に軽いか。
2. 選択したページの左右90°回転が表示にも反映されるか。
3. 削除、上下移動、Undoでページ順・枚数・元ページ表示が整合するか。
4. 「別名保存」で新しいPDFを作り、再度開いてページ順・向き・文字が保持されているか。
5. 元の `sample_40.pdf` と既存ファイルが上書きされないか。
6. 保存中や連続操作中もウィンドウを移動・応答できるか。
7. 画面終了・未保存の変更破棄確認が正常か。

現時点では**90°単位のみ**、ページの並べ替えは**上下ボタン**です。任意角度とドラッグ並べ替えはまだありません。

## エラーの場合
PRレビュー・CI結果・実機結果が揃うまでmainへマージしません。
詳細なWindows情報・失敗時の操作手順・個人情報を含まないログを記録し、原文書のPDFや生徒情報は公開リポジトリへ投稿しないでください。
