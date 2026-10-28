# Python TLS セキュリティ更新（2026-10-23）

このフォークの `uv.lock` は certifi **2026.10.19** をピン留めしています（以前は 2026.5.20）。ソース / pip インストール向けに `certifi>=2026.10.19` の下限も追加し、[GHSA-6q48-6c7w-9gw2](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2) に対応しています。侵害された emSign ECC Root CA - G3 は信頼しません。その他の依存、TLS 検証設定、モデル重み、Python ランタイム要件は変更していません。証明書エラーを検証無効化や削除済みルートの復元で回避しないでください。

GitHub Actions の `Certifi Security Check` は lock を検証し、ハッシュ付き・lock ピン留めの Hugging Face / HTTPX 依存クロージャをインストールします。GPU / モデルコードを読み込まずに実際のダウンロードユーティリティを実行し、削除済みルートのフィンガープリントを確認し、certifi 検証付きの HTTPS を PyPI と公開の MuScriptor assets README に対して行います。Hugging Face トークンやゲート付きモデルのダウンロードは不要です。このチェックはモデル推論・GPU・インストール済みユーザー環境の全面検証ではありません。既存の Node ビルドチェックはそのままです。

既存チェックアウトへこの更新を適用するには、更新済みの `main` を取得し `uv sync --frozen` を実行したうえで、普段の手順でアプリケーションを再起動してください。確認例:

```bash
uv run --frozen python -c "import certifi; print(certifi.__version__, certifi.where())"
```

GitHub 上のマージだけでは、既存環境やコンテナは自動更新されません。継承している PyPI リリースワークフローと Kyutai のデプロイスクリプトはアップストリーム向けであり、このフォークのデプロイ先は確認されていません。この更新はそれらのサービスへ公開しません。別管理のコンテナは、更新済みチェックアウトから再ビルドしてください。
