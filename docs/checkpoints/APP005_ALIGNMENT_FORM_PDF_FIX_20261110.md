# APP-005｜A/BフォームPDF読込修正｜CHECKPOINT（2026-11-10 JST）

- 正本：`moyashimisosoup/pdf-works`、`main`
- [PR #5](https://github.com/moyashimisosoup/pdf-works/pull/5)：マージ済み、merge HEAD `bde094428797b9c56d5778a1149490c02442be5a`
- [Windows CI #42782147432](https://github.com/moyashimisosoup/pdf-works/actions/runs/42782147432)：SUCCESS
- [Linux CI #42782147576](https://github.com/moyashimisosoup/pdf-works/actions/runs/42782147576)：SUCCESS

## 問題
実機でA/B縮尺合わせのAとBを選ぶと、フォーム・署名・添付情報があるためプレビュー前に「A contains forms, signatures or attachments」と表示された。旧実装は読込判定に出力互換性の検査を混在させていた。実際のPDFの構造は機密上アップロードされていないので、どの情報を含むかは未確認。

## 修正
- 暗号化でないPDFの**比較プレビュー**はフォーム/注釈/添付/署名の有無にかかわらず許可。
- 出力時に単なるフォーム属性フラグだけで拒否せず、ページの**実際の**フォーム入力欄・注釈・リンク、添付ファイル、署名フラグを調べる。
- フォーム等により情報欠落があり得るAは、画面上で「表示内容のみ固定して新規PDFにする」旨を表示し、明示的にチェックしたときだけ別名出力する。必要な見える注釈/入力欄はPyMuPDFの`Document.bake(annots=True, widgets=True)`で**メモリ上のコピー**に固定。編集可能な入力欄/リンク/非表示注釈データ/添付は出力に含まれない。
- 電子署名付きAは比較可能だが出力不可。元A/B・既存出力への上書きは禁止。
- PyMuPDFの最小バージョンを1.24.2以上に更新。
- 人工フォーム/添付/署名PDFとQt画面による同意確認のテストを追加。

## 残る確認
- 利用者の当該A・Bファイルで比較表示が成功し、必要な出力ができるかは**未確認**。
- 採点ナビの実物に取り込んだ後、縮尺・位置が合致するかは別途確認。
- ユーザーの学校資料・答案はGitHubに保存しない。

## 次の1操作
利用者PCで最新`main`を再取得し、PDF Worksを再起動。AとBを選んでプレビューする。注意が出た場合は表示内容固定による非表示データ喪失を理解してチェックし、Aを別名保存。元PDFは残す。
