# Windows Qt スクリーンショット生成

`scripts/capture_ui.py` はQtウィンドウの**実際の描画ピクセル**を2枚取得する。出力はGitHub ActionsのArtifactとして14日保存する。

- `pdf-works-qt-normal.png`：立体ボタンの通常状態
- `pdf-works-qt-pressed.png`：「開く」「別名保存」「右90°」が押下中の状態

**重要：これはGitHub ActionsのWindowsホスト上で生成したQt画面プレビューです。ユーザー本人のPCのスクリーンショットではありません。** 画像に表示するPDFは人工生成した40ページの試験データで、PDF描画エンジンのUIワーカーはスクショ専用処理中だけ停止する。Windows実機での機能・操作性・応答性試験とは区別する。

[Windows Qt screenshot workflow](../.github/workflows/ui-screenshot.yml)

手元のWindowsでも同様に保存可能：

```powershell
.\.venv\Scripts\python.exe scripts/generate_test_pdf.py tests/sample_40.pdf --pages 40
$env:QT_QPA_PLATFORM="offscreen"
.\.venv\Scripts\python.exe scripts/capture_ui.py output/ui-screenshots tests/sample_40.pdf
Remove-Item Env:QT_QPA_PLATFORM
```

本物の端末での外観レビューは、通常のアプリを起動しユーザーがWindowsの `Win + Shift + S` で撮影した画面を最終判断に使用する。
