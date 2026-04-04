# CHANGE LOG

## 2026-04-05

- 読了履歴を `data/reading_history.parquet` で管理し、既存の `.book_timer_state.json` から自動移行できるよう改善
- `読了リストに追加` ボタンを追加し、入力中の書名と日付から読了履歴を登録できるよう改善
- Notebook から読了履歴を確認できる `notebooks/reading_history.ipynb` を追加
- 読了履歴の Parquet 保存、JSON 移行、保存順序を検証する回帰テストを追加

## 2026-04-04

- Google カレンダー登録時に失効した `token.json` から自動で再認証へフォールバックするよう改善
- Google カレンダー登録をバックグラウンド実行に変更し、認証中や API 呼び出し中に Tkinter 画面が固まらないよう改善
- Google Calendar API 呼び出しの例外処理を補強し、UI に失敗メッセージを返せるよう改善
- Google 認証キャッシュと登録処理の回帰テストを追加
