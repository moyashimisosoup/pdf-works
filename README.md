# pdf-works

**Lightweight PDF workbench for Windows**  
軽量・高速・シンプルなPDF編集と、全ページ共通領域の切り出し・一覧化を目指すWindowsデスクトップアプリ。

> **状態（2026-10-21）**：`main`はWindows実機で40ページ閲覧等を基本確認したalpha版。`feature/native-page-edit-20261017`はページ編集・ROI一覧・抽出/分割・品質維持最適化を含むbeta版（[Draft PR #1](https://github.com/moyashimisosoup/pdf-works/pull/1)）。betaのGitHub Actions上での自動試験は成功していますが、**利用者Windows PCのbeta全機能E2Eは未確認**です。EXE配布は未実施で、起動にはPythonと依存ライブラリが必要です。

## 開発の原則

1. **操作の応答性を最優先**：UIをPDF描画・保存・OCRから分離し、フリーズを許容しない。
2. **必要な部分だけ処理**：ページ全体や40ページ全件を起動時に高解像度化しない。
3. **共通領域切り出しを基本機能に**：1ページ上の範囲指定を全ページの同じ相対位置へ適用し、タイル一覧・拡大・出力が可能。
4. **元PDFを保護**：編集操作は非破壊で管理し、初期動作は「名前を付けて保存」。無断上書きはしない。
5. **UIはSoft Outline**：単一オフホワイト背景、ふっくらした角丸の輪郭、単色線画アイコン、丸ゴシック系日本語フォント。
6. **OCRは遅延導入**：まず閲覧・ページ編集・共通領域切り出しを安定化してから追加。

## v5で実現する機能

| 順序 | 機能 | 位置付け |
| --- | --- | --- |
| v5.0-alpha | 独立Qtウィンドウ、PDF表示、50〜300%拡大、スクロール | 安定性基盤 |
| v5.0-beta | 回転・削除・並べ替え・取り消し・別名保存 | ページ編集 |
| v5.0 | 共通領域指定、全ページ切り出し、別ウィンドウ一覧、拡大照合、PDF/PNG出力 | 中核 |
| v5.1 | 文字濃度・明るさ・コントラスト補正 | 後続 |
| v5.2 | 手書き番号OCR・訂正・番号順整列 | 後続 |
| v5.3 | 確認済み訂正サンプルの蓄積・モデル評価 | 後続 |

## 技術構成（採用済みと今後の計画）

- UI：**PySide6 / Qt Widgets**（pywebview・ブラウザ内蔵を使わない）
- PDF：**PyMuPDF**（商用/AGPLライセンス条件の確認が必要）
- 描画処理：GUIとは分離したワーカープロセス。PDF文書オブジェクトはプロセス間で共有しない。
- 画像表示：表示中のページと画面内のタイルだけ描画し、キャッシュ容量を制限。
- OCR：標準アプリから切り離したオプション機能（未実装）。
- 配布：将来的にPythonの事前インストール不要なWindows用EXE（onedir形式から検証）。

## ドキュメント

- [製品仕様](docs/SPEC_V5.md)
- [技術構成](docs/ARCHITECTURE.md)
- [UIデザイン](docs/UI_DESIGN.md)
- [性能・フリーズ対策](docs/PERFORMANCE.md)
- [開発計画](docs/ROADMAP.md)
- [試験計画](docs/TEST_PLAN.md)
- [設計決定と未決事項](docs/DECISIONS.md)
- [旧v4系との関係](docs/MIGRATION_V4.md)
- [ライセンス方針（未決）](docs/LICENSING.md)

## ディレクトリ

```text
src/pdf_works/       アプリの将来の実装先
  ui/               Qt Widgetsの画面とモデル
  core/             PDF編集の非破壊モデル・処理
  workers/          描画・出力のワーカープロセス
  resources/icons/  アイコン等（第三者画像は権利確認後）
tests/               自動試験（個人情報を含まない人工PDFを利用）
docs/                正本の仕様と記録
.github/             CI等を必要に応じて設置
```

## 開発・個人情報に関する注意

実際の学校資料、個人情報を含むPDF、手書き数字の生サンプル、個人の出力ファイルはこの公開リポジトリにコミットしないでください。評価データは別の非公開保存先で管理し、公開テストには人工データを使用します。

**alphaの起動（Windows / Python 3.11+）**

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[desktop,dev]"
.venv\Scripts\python.exe -m pdf_works
```

[Windows実機確認手順](docs/ALPHA_RUN.md) / [変更履歴](docs/CHANGELOG.md)

**注意**：この段落の起動コマンドは閲覧用alphaの入口です。betaの保存・切り出し・最適化は開発ブランチで実装済みであり、[Windows beta試験手順](docs/BETA_RUN.md)に従って起動してください。OCRは後続機能です。betaのWindows CIでは人工PDFを用いた40ページQt→実ワーカー最適化E2Eを確認済みですが、利用者PCでのbeta受入は未完了です。

## 編集機能の開発ブランチ

Windowsネイティブのページ編集beta（90°回転、削除、上下移動、Undo、別名保存）を `feature/native-page-edit-20261017` で開発しています。mainは実機動作確認済みの閲覧用alphaを維持します。betaはQt/Windows操作未確認のため、試す際は [beta実機手順](docs/BETA_RUN.md) を先に確認してください。

## フォントと文字の太さ（beta）

- **Zen Maru Gothic** をQtが直接読み込み、Windowsへのフォントインストール不要。
- 初回だけ `.\.venv\Scripts\python.exe scripts/install_fonts.py` を実行。公式OFL配布元から3ウェイトをチェックサム検証付きで取得。
- 起動後は完全オフライン。上部「文字」で **400 / 500（標準）/ 700** を比較し、設定を保持。
- フォントファイルはGitHubに保存せず、配布時はOFLライセンスを同梱。
- 詳細：[文字の視認性評価](docs/TYPOGRAPHY_EVALUATION.md)。Windows Actions上ではQt自動試験を実施済みですが、利用者PCでの表示・DPI確認は未完了です。
