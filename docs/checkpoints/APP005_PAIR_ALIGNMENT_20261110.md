# APP-005 CHECKPOINT｜A/B縮尺合わせ（1組専用）｜2026-11-10 JST

- 正本：`moyashimisosoup/pdf-works`、`main`
- [PR #4](https://github.com/moyashimisosoup/pdf-works/pull/4)：マージ済み
- マージコミット：`df103859ad3a2978d4a12184cc2fb2b614dedda8`
- [Backend CI #42778310085](https://github.com/moyashimisosoup/pdf-works/actions/runs/42778310085)：成功
- [Windows Qt CI #42778310079](https://github.com/moyashimisosoup/pdf-works/actions/runs/42778310079)：成功

## 完成した小さな実用フロー

PDF Works上部の「A/B 縮尺合わせ」から新しいQtダイアログを開く。
A＝取り込み側PDF、B＝固定見本PDFの1組を読み込む。
横並び/半透明重ね表示と不透明度を切り替える。比較は各ファイルの先頭1ページ。
Aの倍率（30〜300％、0.1％刻み）とX/Y位置（±100mm、0.1mm刻み）を調整する。
「調整済みAを別名保存」でAの全ページへ同じ物理的な変形を適用したPDFを出力する。Bの先頭ページの用紙寸法を基準とし、Bは出力しない。

## 重要な境界

- PDF表示/書出しは専用spawnワーカープロセス。元A/B、既存出力は上書きしない。
- 原則ベクター/文字検索を維持するPDF再配置。A内のリンク、注釈、フォーム、電子署名、添付等が失われる可能性のあるものは保存前に拒否。パスワード保護PDFは対象外。
- 単純な均等拡大・縮小＋XY移動のみ。自動位置合わせ、横縦別の拡大率、ページごとの調整、複数ファイル一括処理、テンプレート保存は未実装。
- 利用者Windows PCでのスキャナー原稿・「採点ナビ」実機取り込み結果は未確認。CI上の人工PDF確認と区別する。
- 学校の答案や模範解答のファイルはGitHub等へ送信しない。

## 次の1操作

利用者PCでmain最新版を取得し、`start-pdf-works.cmd`で起動。「A/B 縮尺合わせ」を選び、実際のスキャン答案Aと見本Bの先頭ページの罫線を重ね合わせ、Aの倍率・位置を調整して別名保存、採点ナビに取り込んで確認する。
