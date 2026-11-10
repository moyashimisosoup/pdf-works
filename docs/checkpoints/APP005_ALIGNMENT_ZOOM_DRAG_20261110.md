# APP-005｜A/B重ね合わせ拡大・ドラッグ移動｜CHECKPOINT（2026-11-10 JST）

## 実装・統合
- 正本：[moyashimisosoup/pdf-works](https://github.com/moyashimisosoup/pdf-works) `main`
- [PR #6](https://github.com/moyashimisosoup/pdf-works/pull/6) マージ済み
- マージコミット：`c0a00621362d63e8157b5cda24335494cc0d9fdd`
- [Linux Backend CI #42787298615](https://github.com/moyashimisosoup/pdf-works/actions/runs/42787298615)：SUCCESS
- [Windows Qt CI #42787298556](https://github.com/moyashimisosoup/pdf-works/actions/runs/42787298556)：SUCCESS（重ね合わせ拡大とマウスによるAドラッグ試験を含む）

## 変更内容
1. PDF Works「A/B 縮尺合わせ」の**重ね合わせ表示**に専用`QGraphicsView`を追加。Bの見本を固定したまま、Aを左ドラッグするとXY移動量（mm）が数値欄と同期する。
2. **表示拡大50/75/100/150/200/300/400/600%**。100%は見本Bの全体が表示枠内に収まる倍率、表示だけに適用。拡大時はスクロールで位置を確認。
3. 「画面を最大化/通常サイズ」で比較領域を拡大できる。A/Bファイル欄・上部の表示操作を狭めのWindows画面にも収まりやすく整理。
4. 先頭ページのプレビュー解像度を上限付きで高め、細い線の拡大確認を改善。プレビューはQt GUIの画像で、PDF書き出しは別のspawnワーカーのまま。
5. 既存のA実倍率（%）、X/Yの調整、Bを固定した新規PDF出力、原本・既存ファイルの非上書き、フォーム情報がある場合の出力同意チェックは変更しない。

## 制約・次に確認すること
- 拡大表示は **重ね合わせモード** が対象。左右に並べるモードの拡大は今回未実装。
- A/Bを比較するのはそれぞれ先頭1ページで、Aが複数ページの場合の同一変形一括出力ルールを保持。
- 学校の答案・採点ナビに関する実ファイルの表示・ドラッグ操作・取り込み後の縮尺一致は利用者PCで未検証。CIの合格と混同しない。
- プレビュー/実PDFを公開GitHubへアップロードしない。

## 次の1操作
Windows PCのPDF Worksを終了し、最新`main`から再起動する。「A/B 縮尺合わせ」→「半透明で重ねる」→表示倍率200～300%→Aをドラッグして罫線位置を合わせる→別名保存して採点ナビで確認。
