# ROIのPDFワーカー接続（beta）

2026-10-19時点。対象：`feature/native-page-edit-20261017` のみ。

## 実装した範囲
- `core/crop.py`：表示上の向きに対する正規化ROI (x0,y0,x1,y1) とページ順序をもとにPNGへ切り出し
- `workers/renderer.py`：`roi_export` 要求をspawnワーカー側で処理、QtメインスレッドにPDFレンダリングを持ち込まない
- 元PDFを読み取り専用で利用、既存PNGは上書きしない。処理中エラー時にはこの操作で作られた途中ファイルの削除を試みる
- 36〜300dpi、1出力最大1600万画素。画像はページ単位で順に作成し、40ページを一斉にメモリ保持しない

ワーカー要求例（内部IPC。**UIボタンは未実装**）：

```python
bridge.send(
    "roi_export", generation=current_generation,
    destination_dir="既存の出力フォルダ",
    roi=(0.1, 0.1, 0.45, 0.3),
    pages=edit_session.snapshot(), dpi=200,
)
```

ページIDと追加回転量は`EditSession.snapshot()`から渡す。呼び出し側はまだ画面に接続していないため、今のGUIから切り出しを操作することはできない。

## 未完了
- ドラッグROI選択・修正・確定・表示上のプレビュー
- 複数選択のQt UI接続
- 独立した切り出し一覧ウィンドウ（可視タイルだけ遅延生成）
- 一覧PDFのA4 2×4出力・エクスポート状況/キャンセル・実機操作
- Windows実機の40ページ連続切り出しと保存先衝突の目視確認

自動CIの成功はWindows実機検証の代替ではない。元PDFや個人情報が入るテスト資料は公開リポジトリへ置かない。
