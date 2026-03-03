# Reading Books Timer

デジタルと紙の読書時間を記録し、進捗をリアルタイムで可視化する Tkinter 製のタイマーです。書名・日付・開始終了時刻・ページ数を入力すると、現在どこまで読めているかを分単位で推定し、Googleカレンダーへ登録することもできます。

## スクリーンショット
![Reading Timer screenshot](assets/screenshot.png)

## 主な特徴
- 書名・日付・開始終了時刻・ページ範囲を入力するだけで読書セッションをセットアップ
- 保存済みの書名をドロップダウンから選択可能
- 開始前・終了後の状態を自動判定し、残り時間や最終ページをガイド
- 1 分ごとに推定ページを自動更新
- ウィンドウを閉じても前回の書名・日時・ページ入力を次回起動時に復元
- Googleカレンダーへ読書予定を登録可能
- タイマー本体は追加ライブラリ不要（Googleカレンダー連携時のみ追加インストールが必要）

## 動作環境
- Python 3.10 以降推奨（Tkinter 同梱版）
- Windows 10/11 で動作確認済み

## セットアップ
```powershell
uv sync
```

ランタイム依存関係だけでよい場合:
```powershell
uv sync --no-dev
```

- `uv sync` は `.venv` の作成も兼ねます
- Tkinter は Windows の CPython に同梱される前提です
- Googleカレンダー連携の依存関係は `pyproject.toml` で管理しています

## 起動方法
通常の実行:
```powershell
uv run python book_timer.py
```

または:
```powershell
uv run python -m book_timer
```

ダブルクリック起動:
- ルートの `start_book_timer.cmd` をダブルクリックすると、`book_timer.py` を起動できます
- `.venv\Scripts\python.exe` があればそれを優先し、なければ `py -3` または `python` を使います
- Python が見つからない場合は、エラーメッセージを表示したまま停止します

VSCode から起動:
- `Ctrl+Shift+P` → `Tasks: Run Task` → `Run Book Timer` で起動できます
- 設定ファイルは `.vscode/tasks.json` です

デスクトップショートカット作成:
```powershell
powershell -ExecutionPolicy Bypass -File .\create_book_timer_shortcut.ps1
```
- 実行後、デスクトップに `Book Timer` ショートカットが作成されます
- ショートカットは `start_book_timer.cmd` を参照するため、普段はデスクトップから起動できます

## 使い方
1. ウィンドウ上で書名・日付（`YYYY-MM-DD`、初期値は起動日）・開始時刻（初期値 `08:00`）・終了時刻（初期値 `24:00`）・開始ページ・終了ページを入力
   終了時刻には `24:00` も使えます
2. 書名を入力して `反映` または `Googleカレンダーに登録` を行うと、その書名が次回以降の候補として保存されます
3. 保存済みの書名はドロップダウンから選択でき、不要になった書名は `削除` で一覧から消せます
4. 進捗ラベルに推定ページが表示され、1 分ごとに更新
5. `Googleカレンダーに登録` を押すと、書名とページ範囲を含む予定を Google カレンダーへ登録
6. ウィンドウを閉じると現在の入力内容を保存し、次回起動時に復元
7. 終了予定時刻を過ぎると最終ページ確認のメッセージを表示

## Googleカレンダー連携
1. Google Cloud でプロジェクトを作成し、Google Calendar API を有効化
2. OAuth クライアントを `Desktop app` で作成
3. ダウンロードした OAuth クライアント JSON を、このリポジトリ直下に配置
   `credentials.json` でも、Google が生成した `client_secret_...json` のままでも読み取れます
4. アプリから `Googleカレンダーに登録` を押し、初回のみブラウザでログインして許可
5. 認証後は `token.json` が自動作成され、以後は再利用

- 認証情報ファイルの `credentials.json` と `token.json` は `.gitignore` 済みです
- Google からダウンロードした OAuth クライアント JSON も `.gitignore` 済みです
- 入力内容の復元用ファイル `.book_timer_state.json` も `.gitignore` 済みです
- `.book_timer_state.json` には前回入力した値と書名候補一覧が保存されます
- 認証に失敗した場合は `token.json` を削除してやり直してください

## プロジェクト構成
```
reading_books_timer/
├─ book_timer.py      # エントリーポイント（ロジック + Tkinter UI）
├─ start_book_timer.cmd
├─ create_book_timer_shortcut.ps1
├─ .vscode/
│  └─ tasks.json
├─ modules/
│  ├─ google_calendar.py   # Google Calendar API 連携
│  └─ session_state.py     # 入力内容の保存と復元
└─ assets/            # 画像・フォント・CSV 等のリソース（必要に応じて作成）
```

- ロジック関数（時間計算やページ推定）はファイル冒頭付近にまとめ、Tkinter ウィジェット組み立ては末尾に配置する方針です。
- 新しい計算ヘルパーや設定値は `modules/` に分割し、`book_timer.py` からインポートしてください。

## 開発メモ
- コードスタイル: PEP 8（4 スペースインデント、snake_case 変数・関数、PascalCase クラス）
- ユーザーに表示する文字列は重複させず、再利用しやすく管理
- テキストは UTF-8（日本語＋英語混在可）

### テスト & 検証
- メイン: 手動検証  
  `uv run python book_timer.py` を実行し、開始前／進行中／終了後で表示が正しいか確認  
  `24:00` 指定時にクラッシュせず継続することも確認
- 自動テスト（任意）: `tests/test_*.py` を追加し、計算関数を GUI から切り離して検証  
  ```powershell
  uv run pytest
  ```

## 今後のアイデア
- 休憩リマインダーの追加
- CSV やグラフへのセッション履歴エクスポート
- GUI のテーマやアイコンカスタマイズ（`assets/` フォルダ活用）

## ライセンス
- MIT License ([LICENSE](LICENSE))




