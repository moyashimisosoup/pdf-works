# v5.0-beta Windows試験（開発ブランチ専用）

**対象**：`feature/native-page-edit-20261017`。mainの動作確認済みalphaとは別の未検証版です。

## 起動まで

既にGit clone済みの `pdf-works` ディレクトリから：

```powershell
git fetch origin
git switch feature/native-page-edit-20261017
.\.venv\Scripts\python.exe -m pip install -e ".[desktop,dev]"
# 初回セットアップだけ：公式Zen Maru Gothicを取得・検証し、アプリ専用フォルダへ配置
.\.venv\Scripts\python.exe scripts/install_fonts.py
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

## UIの書体・太さを実機で比較する
- アプリ上部「文字」で、やわらか（Regular 400）／標準（Medium 500）／くっきり（Bold 700）を切り替える。初期値は標準。
- 「書体：Zen Maru」と表示されたら、ローカル配置したアプリ専用フォントを認識。代替と出る場合、上記インストールスクリプトを実行しアプリを再起動。
- 起動後のネット通信・Windowsへのフォントインストールは不要。フォントの初回取得にはネット接続が必要。
- 日本語の「削除／元に戻す／別名保存」、薄い補足文字、PDFページ一覧を125%・150%表示倍率でも比較し、線が細く感じないものを選ぶ。
- フォントファイルはGitHubには保存せず、配布版EXE/フォルダへ同梱する際はOFL.txtを含める。
