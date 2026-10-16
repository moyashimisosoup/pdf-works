# Zen Maru Gothic：アプリ専用フォント

このフォルダには、配布元から検証済みのフォントを**セットアップ時に配置**します。

```powershell
.\.venv\Scripts\python.exe scripts/install_fonts.py
```

- 取得先：<https://github.com/googlefonts/zen-marugothic>
- 固定コミット：`553c872b216d1290e2902a466edcdc9682f0df6a`
- 書体：Regular 400、Medium 500、Bold 700
- 取得物：3つのTTFと `OFL.txt` （SIL OFL 1.1）
- 内容：GitオブジェクトのSHA-1を検証し、整合しないものは使用しない
- 実行時：外部接続・Windows全体へのフォント登録は行わない
- フォント本体の容量：約11.4MB、配布サイズ・起動時間はWindows実機で再測定する

フォント本体を公開GitHubにコミットする必要はありません。将来のWindows EXEに同梱する場合、同じOFL.txtを必ず含めます。
