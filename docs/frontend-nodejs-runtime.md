# フロントエンド Node.js ランタイム（2026-10-21）

Docker のフロントエンドビルダーとリリースワークフローは Node.js 26.12.1 を使います。Bookworm Slim のビルダーイメージは digest でピン留めしています。pnpm は既存の `web/package.json` のバージョン 10.20.0 のままです。Node.js 26 は Corepack を同梱しないため、pnpm は明示的にインストールします。frozen lockfile でのインストール、Python 依存、モデル重み、ランタイムの挙動は変更していません。

フロントエンド開発では Node.js 26.12.1 と `npm install --global pnpm@10.20.0` を使い、`web/` で次を実行します。

```bash
pnpm install --frozen-lockfile && pnpm run build
```

GitHub Actions の `Node Runtime Check` は TypeScript/Vite ビルドと Docker の `web-builder` ステージを検証します。パッケージの公開、Python サービスの起動、モデル重みのダウンロードは行いません。
