# CI: バックエンド最小試験

- GitHub Actions の `backend-tests.yml` は、PRの関連ファイル変更・main更新・手動起動時だけ動く。
- Python 3.12 / Ubuntuで**PyMuPDF処理と編集モデルの自動テスト**を実行。QtやWindowsのGUI実機動作を証明するものではない。
- 権限は `contents:read` のみ、同一ブランチの旧実行をキャンセルし、1回の制限時間は8分。
- 結果が成功しても、Windowsでの「応答なし」再発防止、EXE配布、源柔ゴシックとライセンスの条件が完了したわけではない。
- GitHub Actionsの実行結果は `Actions` ページで個別に確認し、未実施または失敗を成功済みと報告しない。
