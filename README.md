# Memories-AI

「ユーザーとの会話を記憶する AI キャラクター付きチャットアプリ」の最小構成です。バックエンドは FastAPI + OpenAI Responses API（Agents SDK でツール呼び出し）、フロントは Vite + React + TypeScript で構成しています。短期/長期メモリは Markdown ファイルとしてローカル保存します。

## 機能概要

- モデル: 既定 `gpt-5-mini`（環境変数で上書き可）
- 推論: OpenAI Responses API（/v1/responses）を使用
- エージェント: OpenAI Agents SDK
  - 必要時のみメモリ取得ツールを呼び出す（retrieve_memories）
  - 重要情報は長期メモリへ格納（save_long_term_memory）
- メモリ
  - 短期: `memory/short/YYYY-MM-DD.md` に会話を追記
  - 長期: `memory/long/long-term.md` に極小要約（重複指紋付き）
  - 3日/7日要約、14日削除のメンテ関数あり（任意実行・起動時実行オプション）
- SSE ストリーミング: `/api/chat/stream` でモデルのトークンを逐次配信

## ディレクトリ構成（主要）

- `backend/`
  - `app.py` FastAPI アプリエントリ
  - `config.py` 環境変数読み込みと OpenAI クライアント生成
  - `models.py` API 入出力の Pydantic モデル
  - `routes/chat.py` チャット API（同期/ストリーム）
  - `routes/memory.py` メモリ参照とメンテ実行 API
  - `agent/character.py` エージェント定義＆ツール
  - `agent/runner.py` Responses API 呼び出し（同期/ストリーム）
  - `memory/manager.py` メモリ入出力・指紋・インデックス
  - `memory/summarizer.py` 3日/7日要約・14日削除
- `frontend/` Vite + React + TypeScript
  - `index.html`, `src/App.tsx`, `src/main.tsx`, `src/styles.css`
  - `package.json`, `tsconfig.json`, `vite.config.ts`
- `memory/` 実データ（初期ファイルあり）
  - `short/.gitkeep`
  - `long/long-term.md`
  - `index.json`
- `requirements.txt` バックエンド依存
- `.env.example` 環境変数の例（OpenAI 版 / gpt-oss 版）

## 前提

- Python 3.10+
- Node.js 18+（推奨: 20+）

## セットアップと起動

1) 依存のインストール（Python）

```bash
# uv を使う場合
uv pip install -r requirements.txt

# もしくは通常の pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) 環境変数の設定（.env）

`.env.example` を参考に `.env` を作成してください。利用形態は2パターンあります。

- Option A: OpenAI（クラウド）
  - `OPENAI_API_KEY=sk-...`
  - `OPENAI_MODEL=gpt-5-mini`（省略時もこれ）
- Option B: ローカル gpt-oss（バックエンド: Ollama）＋ Responses API サーバ
  - 事前準備
    - `pip install gpt-oss`
    - `ollama pull gpt-oss:20b`
    - `python -m gpt_oss.responses_api.serve --inference-backend ollama --port 8080`
  - アプリ側 `.env`
    - `OPENAI_BASE_URL=http://localhost:8080/v1`
    - `MODEL=gpt-oss:20b`
  - 備考: ローカルサーバは API キー不要です（プレースホルダで動作）。

3) バックエンド起動

```bash
uv run uvicorn backend.app:app --reload
# または
uvicorn backend.app:app --reload
```

4) フロントエンド起動

```bash
cd frontend
npm install
npm run dev
```

- 既定で `http://localhost:5173` が開きます。
- 開発時は Vite のプロキシが `/api` を `http://localhost:8000` に転送します。

## 使い方（API 概要）

- `POST /api/chat`
  - 入力: `{ "message": string, "sessionId?": string }`
  - 処理: エージェントが必要に応じてメモリを取得 → Responses API で生成 → 短期へ追記、長期候補抽出
  - 出力: `{ "message": string, "usage?": any, "memoryActions?": any }`

- `GET /api/chat/stream?message=...`
  - SSE でモデルのトークンを逐次送信（`data: <delta>`、終了時 `event: done`）
  - 生成終了後に短期/長期メモリへ反映

- `GET /api/memory/short?date=YYYY-MM-DD`
  - 指定日の短期メモリ Markdown を返却

- `GET /api/memory/long`
  - 長期メモリ Markdown を返却

- `POST /api/memory/maintain`
  - 3日/7日要約・14日削除を一括実行（都度実行）

## キャラクター画像の設定

初期状態ではダミーのSVG画像を使用しています（`frontend/src/assets/avatar.svg`）。画像の差し替え方法は用途に応じて次の2通りです。

- 方法A: 画像URLを環境変数で指定（推奨・最も簡単）
  1. `frontend/public/` に画像を配置（例: `frontend/public/character.png`）。
  2. `frontend/.env.local` を作成し、以下を記載:
     ```
     VITE_CHARACTER_IMAGE_URL=/character.png
     ```
  3. `npm run dev` を再起動。`SidePanel` の画像が差し替わります。
  - ポイント: `VITE_` プレフィックスは Vite のクライアント向け環境変数。相対パス（`/character.png`）のほか、CDN 等の絶対URLも指定可能です。

- 方法B: リポジトリ内のダミーSVGを置き換える
  - `frontend/src/assets/avatar.svg` を任意のSVGやPNGに差し替え、`App.tsx` の import をそのまま利用。

スタイルは `frontend/src/styles.css` の `.avatar-img` を調整してください（円形・枠線・サイズなど）。推奨は正方形（例: 256x256）・背景透過PNGです。

## メモリの仕様

- 短期: `memory/short/YYYY-MM-DD.md`
  - `- [HH:MM] user|ai: ...` を追記
- 長期: `memory/long/long-term.md`
  - `- YYYY-MM-DD | category: text | #tag | fp:xxxxxx`
  - 重複を指紋（SHA1短縮）で抑止
- ライフサイクル
  - T+3日: 要約（5行以内）
  - T+7日: さらに要約（3行以内）
  - T+14日: 短期関連ファイル削除

## 起動時のメンテ（任意）

- `.env` に `MEMORY_MAINTAIN_ON_START=1` を設定すると、サーバ起動時に `daily_maintain()` を一度実行します。
- 手動実行は `POST /api/memory/maintain` を使用してください。

## 設定（主な環境変数）

- `OPENAI_API_KEY`: OpenAI API キー（クラウド利用時）
- `OPENAI_MODEL` or `MODEL`: 既定は `gpt-5-mini`（例: `gpt-oss:20b`）
- `OPENAI_BASE_URL`: OpenAI 互換のベース URL（例: `http://localhost:8080/v1`）
- `MEMORY_ROOT`: メモリ保存ルート（既定 `./memory`）
- `MEMORY_MAINTAIN_ON_START`: 起動時に 3d/7d/14d メンテ実行（`1` で有効）

## 開発メモ

- エージェントは Agents SDK を利用し、ツール呼び出し（retrieve_memories / save_long_term_memory）を自律判断します。
- SSE は Responses API のストリーミングイベント（`response.output_text.delta`）をそのまま転送します。
- `.env` が未設定でも致命的に落ちない設計です。`OPENAI_API_KEY` がない場合は、`OPENAI_BASE_URL` （OpenAI互換サーバ）を設定してください。

## ライセンス

本リポジトリのライセンス表記がない限り、社内・個人検証用途を想定しています。詳細は運用方針に従ってください。
