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

## 人工40ページの受入補助（推奨・2026-10-21追加）

従来の`tests/sample_40.pdf`と併用できます。新しい補助スクリプトは**元PDFを上書きせず**、受入試験専用の人工40ページPDF・原本SHA-256・チェックリストを`output/beta-acceptance/run-.../`内に生成します。`output/`はGit管理の対象外です。

ブランチを最新にした後、既存の仮想環境から以下を実行します。

```powershell
git fetch origin
git switch feature/native-page-edit-20261017
git pull --ff-only origin feature/native-page-edit-20261017
.\.venv\Scripts\python.exe scripts/windows_beta_acceptance.py prepare
.\.venv\Scripts\python.exe -m pdf_works
```

1. `prepare`実行時に出力される`source_40.pdf`のパスを確認し、起動したPDF Worksで開く。
2. 同じフォルダにある`manual-checklist.md`に沿い、Ctrl/Shift複数選択・編集/Undo・ROI PNG・ギャラリー・A4一覧PDF・抽出/分割・画面操作性を実機で確認する。
3. 未保存編集がない状態で「容量を最適化」→ **同じ実行フォルダの`optimized.pdf`として新規保存**する。もし既に存在したら上書きせず、新たな`prepare`実行フォルダで試す。
4. PDF Worksを閉じた後、同じリポジトリのPowerShellから以下を実行する。

```powershell
.\.venv\Scripts\python.exe scripts/windows_beta_acceptance.py verify
```

`verify`は直近の試験フォルダを自動選択し、`verification.json`へ**原本SHA-256の不変、容量の前後差、全40ページの文字・寸法・回転、先頭/中央/末尾ページの描画一致**を保存します。PDFがまだ出力されていない場合は`incomplete`、差異・破損時は`fail`を返します。`pass`も**自動内容照合の合格**に限り、クリック・フリーズ・DPIの実機操作まで合格したことにはなりません。手動チェック結果も必ず別に記録してください。

学内資料・個人情報入りPDFは受入補助に渡さず、試験データ・`verification.json`・端末情報を公開GitHubへアップロードしないでください。

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

## 品質維持最適化のWindows実機チェック（2026-10-20追加）

最初は`tests/sample_40.pdf`のような**人工PDF**で試してください。学内・個人情報を含むファイルはGitHubへアップロードしません。

1. PDFを開き、ヘッダーに実ファイル容量が表示されることを確認する。
2. 「容量を最適化」を押し、**新しいファイル名**（例：`sample_40_optimized.pdf`）を選んで保存する。
3. 完了メッセージが元PDFの容量 → 新PDFの容量と「削減」「増加」「変化なし」を正しく表示することを確認する。**必ず縮小するわけではありません**。
4. 新しいPDFを開き、ページ数、見た目、全文検索、しおり、回転を比較する。元のPDFは変更されないことを確認する。
5. 既存の出力先ファイル名を再指定した場合、**上書きしない**ことを確認する。
6. 回転などページ編集を加えて未保存にすると「容量を最適化」は無効化される。先に「別名保存」してそのPDFを開き直した後に試す。
7. フォーム・電子署名・添付ファイル・暗号化PDFは安全上このモードで拒否される。個別に自動解除や変換を試みない。
8. 40ページでウィンドウを移動したり別ウィンドウに切り替え、重いPDF保存中もGUIがフリーズしないか確認する。

PowerShellで元PDFと結果の容量および原本SHA-256を比較できます。

```powershell
Get-Item .\tests\sample_40.pdf, .\tests\sample_40_optimized.pdf |
  Select-Object Name, Length
Get-FileHash .\tests\sample_40.pdf -Algorithm SHA256
```

原本ハッシュは最適化前にも確認し、最適化後と**同じ値**であることを確認してください。新しいPDFのハッシュは変わって当然です。

自動CI成功と利用者PCの実機結果は別々に記録し、未確認の操作を完了と扱いません。
