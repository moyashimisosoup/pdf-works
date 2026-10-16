# v5アーキテクチャ
状態：設計段階（コード実装前）

## 原則：ネイティブUIと重いPDF処理を分離
- **UI**：PySide6 / Qt Widgets。QMainWindow、ページ一覧、PDF表示、設定パネル、切り出し一覧QDialog/QWidget。
- **PDFコア**：PyMuPDF。ファイルから表示・切り出し・出力を担当。
- **非破壊状態**：原本パス、ページID、編集順序、除外ID、ページ回転、ROI、選択状態。元PDFへ直接保存しない。
- **ワーカー**：Windowsのspawn方式を想定した別プロセス。PyMuPDFのdocument/page等は共有・pickle送信せず、ワーカー側でファイルを開く。
- **UIプロセス**はQtのメインスレッドでPDF描画をしない。IPC受信はQtイベントループを塞がない方法で扱う。

```text
Qt GUI (UI thread)
 ├─ AppState / EditCommands / Undo
 ├─ Viewer / PageList / CropGallery
 └─ Request Dispatcher ── IPC ──> PDF worker process
                                   ├─ open(metadata)
                                   ├─ render(page, clip, scale)
                                   ├─ crop(page, normalized ROI)
                                   └─ export(snapshot, destination)
```

## 描画のルール
- 初期表示：メタデータと現在ページの低解像度プレビューを要求。
- プレビュー：現在の表示位置を優先し、ズーム時は近い表示領域を必要解像度で描画。
- 一覧サムネイル：QAbstractListModel + 可視範囲の遅延リクエスト。
- 切り出し一覧：QAbstractItemModel / 仮想化したグリッドで可視タイルのみ生成。
- 頻繁なページ送り・ズーム変更では単調増加request_idを発行し、古い結果は破棄。
- 要求の種類別に優先度を付ける（現ページ > 操作中の切り出し > 可視サムネイル > 先読み）。
- LRUキャッシュの容量をバイト数で計測し、初期上限64MiBを超えた画像を順次破棄。
- 画像データはバックエンドで所有し、GUIへQImageを安全に受け渡す。サイズと所有権の検証を行う。

## コアの責務
- `document.py`：PDFの読取メタデータ、開閉、ページ識別。
- `page_edit.py`：編集コマンド（remove/reorder/rotate）と履歴（Undo）。
- `crop.py`：ROIの正規化、ページ方向・座標系との変換、切り出し範囲。
- `export.py`：元ファイル保護、書き込み前検証、別名保存、一覧PDF/PNG生成。
- `workers/pdf_worker.py`：プロセス境界とIPC、要求のキャンセル/結果の返却。

各名称は**予定ファイル**。現時点で処理を実装したという意味ではない。

## 安全性・エラー
- 元PDFと出力先は解決済み実パスで比較する。大文字/小文字、リンク、実パス表記の差に注意。
- 作業中の編集はアプリのメモリ状態。書き出しは明示的に指示された場合だけ実行。
- 未処理・例外・タイムアウト時は通知し、GUI操作と閉じる動作は維持する。
- ワーカープロセスが失敗した場合は再起動可能にし、ユーザーの編集モデルを保持する。
- パスワード保護PDFは適切なエラー/入力を表示。破損ファイルでもプロセス全体を落とさないこと。

## 依存関係とライセンス
- PySide6 / Qt Widgets採用予定。
- PyMuPDF採用予定。ただしAGPLv3/商用条件の確認を完了するまで配布ポリシーを確定しない。
- OCR・Tesseractはv5.0の依存から外す。
- WebView2埋め込み(pywebview)はフリーズ経験から標準GUIに採用しない。
