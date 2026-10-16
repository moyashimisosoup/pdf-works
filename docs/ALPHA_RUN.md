# v5.0-alpha Windows実機確認

**状態：Windows実機試験前。現在のalphaはPDF閲覧専用です。**

## 動作環境と導入

Python 3.11以上を使います。alpha段階ではEXE化未実施のため事前導入が必要です。

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[desktop,dev]"
.venv\Scripts\python.exe scripts/generate_test_pdf.py tests/sample_40.pdf --pages 40
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pdf_works
```

PySide6とPyMuPDFの導入にネット接続が必要な場合があります。アプリ本体は外部WebフォントやWebView2を必要としません。

## 検証手順

1. 独立したQtウィンドウが開き、空画面で「開く」ボタンが反応する。
2. 人工PDF `tests/sample_40.pdf` を読み込み、40ページ表示を確認する。
3. 前/次ページを各10回連続で操作しても応答なしにならない。
4. 50→100→200→300%に切り替え、スクロールとページ表示が追従する。
5. 拡大したままウィンドウを移動・縮小・最大化・終了できる。
6. 画面幅を小さくしてもページ一覧とプレビューが重ならない。
7. 原本PDFが変更されていない（alphaは閲覧専用）。
8. 以前フリーズが起きた別Windows端末でも同じ操作を確認する。

## 記録すべき情報

Windowsバージョン、CPU、メモリ、表示倍率、Python/PySide6/PyMuPDFの各バージョン、起動時間、固まる直前の操作、エラー全文。個人情報を含むPDFや個人名・実パスは公開Issueに貼らない。

## 今回実施できたことと限界

- 人工40ページPDFで描画・サムネイル・3倍描画・spawnによるプロセス間通信の自動テストを計5件実施し成功。
- Pythonコードの構文検証は成功。
- この開発環境にはPySide6がなく、追加インストールもネットワーク制限で不可。**Qt GUI起動・Windows実機・EXEは未確認**。
- 回転・削除・並べ替え・共通領域切り出し・OCRは未実装。
