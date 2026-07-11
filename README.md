# Book Timer

読書セッションの予定、進捗、読了履歴、Googleカレンダーをまとめて扱うローカルWebアプリです。Reactの画面をFastAPIが配信し、サーバーは `127.0.0.1` のみに公開します。

## 主な機能

- 書名、開始・終了日時、ページ範囲から読書セッションを設定
- 現在時刻に応じた推定ページ、進捗率、残り時間をリアルタイム表示
- 入力内容と書名候補を自動保存し、次回起動時に復元
- 読了履歴の追加・削除と、累計・年別・月別冊数の表示
- Googleカレンダーへの読書予定登録
- Googleカレンダーの今日の予定を、終日・時刻付きで一覧表示
- `24:00` や `25:00` など翌日扱いの時刻に対応
- デスクトップ、タブレット、モバイル幅に対応

## 構成

```text
book-timer/
├─ frontend/                  # React + TypeScript + Vite
│  ├─ src/
│  │  ├─ components/
│  │  ├─ api.ts
│  │  ├─ App.tsx
│  │  └─ styles.css
│  └─ package.json
├─ modules/
│  ├─ google_calendar.py     # Google Calendar API
│  ├─ reading_history_store.py
│  ├─ reading_session.py     # UI非依存のセッションロジック
│  └─ session_state.py
├─ tests/
├─ web_app.py                # FastAPI + React配信
├─ start_web_app.cmd         # Web版の起動
└─ book_timer.py             # 移行確認用のTkinter版
```

## 必要環境

- Python 3.10以降
- [uv](https://docs.astral.sh/uv/)
- Node.js 20以降とnpm

## セットアップ

```powershell
uv sync
cd frontend
npm install
npm run build
cd ..
```

## 起動

Windowsでは、リポジトリ直下の `start_web_app.cmd` をダブルクリックします。依存関係が未導入の場合は自動でセットアップし、フロントエンドをビルドしてからブラウザを開きます。

デスクトップへ `Book Timer` ショートカットを作成・更新する場合:

```powershell
powershell -ExecutionPolicy Bypass -File .\create_book_timer_shortcut.ps1
```

作成後はデスクトップの `Book Timer` アイコンをダブルクリックするだけで起動できます。すでにサーバーが動作中の場合は、二重起動せず既存画面をブラウザで開きます。

PowerShellから起動する場合:

```powershell
uv run python web_app.py
```

起動後のURL:

```text
http://127.0.0.1:8000
```

サーバーはローカルループバックにだけバインドされ、LANやインターネットには公開されません。停止するときは起動したターミナルで `Ctrl+C` を押します。

## 開発

バックエンドとフロントエンドを別々に起動すると、Reactの変更が即時反映されます。

ターミナル1:

```powershell
uv run uvicorn web_app:app --host 127.0.0.1 --port 8000 --reload
```

ターミナル2:

```powershell
cd frontend
npm run dev
```

開発画面は `http://127.0.0.1:5173`、API仕様は `http://127.0.0.1:8000/api/docs` で確認できます。

## Googleカレンダー連携

1. Google CloudでGoogle Calendar APIを有効化
2. OAuthクライアントを `Desktop app` として作成
3. ダウンロードしたJSONをリポジトリ直下へ配置
   - `credentials.json`
   - または `client_secret_...json`
4. Web画面の「今日の予定」の更新、または「予定を登録」を実行
5. 初回だけブラウザでGoogleアカウントへのアクセスを許可

認証後は `token.json` が作成され、次回以降は再利用されます。予定の取得対象はログインしたアカウントのprimaryカレンダーです。

`credentials.json`、`client_secret_...json`、`token.json` は `.gitignore` の対象です。Reactへ認証情報やOAuthトークンを渡すことはありません。

## データ保存

- 入力内容・書名候補: `.book_timer_state.json`
- 読了履歴: `data/reading_history.parquet`
- Google OAuthトークン: `token.json`

既存のTkinter版と同じファイルを利用するため、過去の入力内容と読了履歴をそのままWeb版へ引き継げます。

## テスト

Python:

```powershell
uv run pytest -p no:cacheprovider
```

Reactの型チェックと本番ビルド:

```powershell
cd frontend
npm run build
```

## Tkinter版

移行結果の比較用として従来版も残しています。

```powershell
uv run python book_timer.py
```

新規機能はWeb版へ追加する方針です。

## ライセンス

MIT License
