# Memories-AI

## 概要

このプロジェクトは、エージェントライクな AI チャットボットの一環として、「ユーザーとの会話を記憶する AI キャラクターを備えたチャットアプリ」を開発するものである。

## 要件定義

### 要件 1. 技術スタック

- バックエンド（ユーザー入力の処理や OpenAI-API との通信など）: Python
- フロントエンド（チャット UI）: TypeScript

### 要件 2. バックエンド

- AI モデル: OpenAI "gpt-5-mini"
- API: OpenAI Responses API
  - 必ず次のドキュメントを参照して使用すること（https://platform.openai.com/docs/api-reference/responses）
- Agent SDK: OpenAI Agents SDK
  - 必ず次のドキュメントを参照して使用すること（https://openai.github.io/openai-agents-python/）
- キャラクター: まずは一般的な女性キャラクターとし、プロンプトで詳細のチューニングができるようにする。

### 要件 3. 記憶について

- 短期メモリ
  - AI キャラクターは、ユーザーとの会話の内容を短期メモリとして Markdown 形式のファイルに記録する。
  - 短期メモリの内容は、その会話が行われてから 3 日後に要約され、7 日後にさらに簡潔に要約され、14 日後に完全に削除される。
- 長期メモリ
  - AI キャラクターは、ユーザーとの会話の内容の中で、特に重要だと思った情報（ユーザーの好きなもの、されて嫌だったこと、など）、繰り返し言われた情報、強く印象に残った情報（ユーザーがキャラクター AI にとって嬉しい言葉をかけてくれた、など）を、極めて簡潔に抜き出して長期メモリとして Markdown 形式のファイルに記録する。
  - 長期メモリの内容は、基本的に削除されない。
- 情報へのアクセス
  - AI キャラクターがユーザーと会話する際には、短期および長期メモリの内容を必要に応じてコンテキストとして参照できる。
    - すなわち、AI キャラクターが「思い出さなきゃ」と考えたことをトリガーとして、短期および長期メモリの情報群にアクセスする。
    - 技術的には、メモリの内容をすべて統合してテキスト形式のままユーザークエリに追加し、LLM に渡すこととする。

### 要件 4. フロントエンド

- チャット UI はオーソドックスでシンプルなものとする。
  - 画面下部にユーザーの入力フィールドを配置する。
  - 入力フィールドの上方には、同一セッションにおけるこれまでの会話が表示される。
  - チャット UI の右部に、AI キャラクターの画像（または動画・リアルタイム CG アニメーションなど）を表示するフィールドを配置する。
  - バックグラウンドはパステルブルー（#A1C1E6）
  - テキストカラーはダークグレー（#101010）

---

## 詳細仕様（Responses API + Agents SDK 準拠）

本章では、OpenAI Responses API と OpenAI Agents SDK の公式ドキュメントに準拠しつつ、本プロジェクトのバックエンド／フロントエンド／メモリ管理の詳細設計を定義する。

### 全体アーキテクチャ

- 構成: フロントエンド（TypeScript/React）＋ バックエンド（Python/FastAPI）
- モデル: 既定で `gpt-5-mini`（環境変数で上書き可能）。
- 推論 API: OpenAI Responses API（`/v1/responses`）。
- エージェント制御: OpenAI Agents SDK（エージェント定義、ツール呼び出し、セッション管理）。
- メモリ:
  - 短期メモリ（Markdown, 日次ファイル）
  - 長期メモリ（Markdown, 重要情報の極小要約）
  - 参照: 会話中に「思い出す」必要があるときに、エージェントがツール呼び出しでメモリを取得し、LLM コンテキストに取り込む（Responses API に渡す入力テキストへ結合）。

### バックエンド設計（Python/FastAPI）

- バージョン/依存関係（例）
  - Python 3.10+
  - `fastapi`, `uvicorn`
  - `openai`（Responses API クライアント）
  - `openai-agents`（Agents SDK）
  - `pydantic`, `python-dotenv`
  - スケジューラ: `APScheduler` もしくは OS の cron（運用方針により選択）

- 環境変数
  - `OPENAI_API_KEY`: OpenAI API キー
  - `OPENAI_MODEL`: 省略時は `gpt-5-mini`
  - `MEMORY_ROOT`: メモリ格納ルート（省略時は `./memory`）

- ディレクトリ構成（提案）
  - `backend/`
    - `app.py`（FastAPI エントリ）
    - `agent/`
      - `character.py`（エージェント定義・プロンプト・ツール）
      - `runner.py`（Agents SDK Runner/Session ラッパー）
    - `memory/`
      - `manager.py`（保存・読込・要約・削除の業務ロジック）
      - `summarizer.py`（Responses API を用いた要約）
    - `routes/`
      - `chat.py`（チャット API）
      - `memory.py`（メモリ参照 API）
    - `models.py`（Pydantic スキーマ）
  - `memory/`（実データ: リポジトリ直下、単一ユーザー前提）
    - `short/`（短期メモリ: 日次ファイル）
      - `2025-09-01.md`
    - `long/`（長期メモリ: 重要情報集約）
      - `long-term.md`
    - `index.json`（短期ファイルの状態・次回処理日時など）

- キャラクタープロンプト（ベース）
  - 一般的な女性キャラクター。丁寧・親しみやすい口調。ユーザーの心情に配慮し、短く明瞭に回答。必要時のみメモリ参照ツールを呼び出す。
  - 例: 「必要だと思ったときだけ、`retrieve_memories` ツールで過去の短期/長期メモリを取り出してから回答を続ける。」

- Agents SDK によるエージェント定義（概略）
  - エージェント本体: `Agent(name="Assistant", instructions=キャラクタープロンプト, model=OPENAI_MODEL)`
  - ツール定義（関数ツール）
    - `retrieve_memories(query?: str, days?: int)`
      - 概要: 短期/長期メモリから関連テキストを収集して返す。
      - 実装: `memory/manager.py` を呼出し、Markdown を整形して返却。
    - `save_long_term_memory(text: str, category?: str)`
      - 概要: 重要/反復/印象的な事項を極小要約として `long-term.md` に追記。
      - 実装: 重複検知のためハッシュ（指紋）を併記。
  - セッション
    - 単一ユーザーかつ単一セッション前提のため、固定セッションID（例: `default`）。
    - 必要に応じて Agents SDK の `SQLiteSession` をオプション採用（トークン節約）。

- Responses API 呼び出し（要点）
  - 基本形（同期）
    ```python
    from openai import OpenAI
    client = OpenAI()

    response = client.responses.create(
        model=OPENAI_MODEL,  # 既定: "gpt-5-mini"
        input=merged_text  # ユーザー発話 + 必要時メモリ結合テキスト
    )

    # 出力テキスト抽出（Responses API の response.output[*].content[*].text を想定）
    def extract_text(resp):
        for item in (resp.output or []):
            if item.get("type") == "message":
                for part in item.get("content", []):
                    if part.get("type") == "output_text":
                        return part.get("text")
        return ""
    ```
  - ストリーミングは後述のフロントエンド仕様と整合すれば SSE/WebSocket で拡張可。

- メモリ設計（ファイル仕様）
  - 短期メモリ（`memory/short/YYYY-MM-DD.md`）
    - 形式: Markdown。タイムスタンプと話者を付与し、会話を時系列追記。
    - 例:
      ```md
      # 2025-09-01 (short-term)
      - [10:02] user: 今日は少し疲れています。
      - [10:03] ai: 無理せずいきましょう。何が一番負担ですか？
      ```
  - 長期メモリ（`memory/long/long-term.md`）
    - 形式: Markdown 箇条書き。極小・非冗長。カテゴリ/指紋を併記。
    - 例:
      ```md
      - 2025-09-01 | like: 紅茶が好き | #likes | fp:2b5c...
      - 2025-09-01 | avoid: 大きな音が苦手 | #dislikes | fp:a9ff...
      ```
  - インデックス（`memory/index.json`）
    - 各日次ファイルの「作成日時」「3日/7日/14日の処理予定日時」「状態（raw/3d/7d/deleted）」などを保持。

- メモリのライフサイクル（要件準拠）
  - T+0: 短期メモリとして記録。
  - T+3日: 短期メモリを要約（`YYYY-MM-DD.summary.3d.md` を作成 or 該当ファイル末尾に Summary セクション追記）。
  - T+7日: さらに簡潔に要約（`YYYY-MM-DD.summary.7d.md` を作成 or 置換）。
  - T+14日: 原文・要約含め短期メモリを完全削除。
  - 長期メモリは基本削除しない。

- メモリ参照のトリガ（「思い出す」）
  - エージェントは通常の応答生成前に、必要と判断した場合のみ `retrieve_memories` ツールを呼ぶ。
  - ツール結果のテキストをユーザー入力と結合し、Responses API に渡す入力（merged_text）とする。
  - これにより「必要なときだけ思い出す」という要件と、「テキストとして統合して LLM に渡す」という技術要件を同時に満たす。

- 要約/抽出（Responses API プロンプト指針）
  - 3日要約: 「会話の要点をMarkdown 箇条書きで5行以内、固有名詞と好悪のみ強調」
  - 7日要約: 「さらに圧縮。固有名詞/習慣/好悪のみに限定。3行以内」
  - 長期抽出: 「ユーザー個性/好悪/繰返し言及/喜怒哀楽を極小要約で1-2行、カテゴリ付与（like/dislike/habit/other）」

- バックグラウンド処理（スケジューリング）
  - `APScheduler` で 1日1回（深夜帯）に `index.json` をスキャンし、期限に達したファイルを Responses API で要約→保存/削除。
  - 代替: OS の cron で `python -m backend.memory.summarizer` を1日1回実行。

- API エンドポイント（案）
  - `POST /api/chat`
    - 入力: `{ message: string, sessionId?: string }`
    - 処理: Agents SDK Runner でツール利用を許可。ツールで取得したメモリを結合し Responses API で応答生成。短期メモリに追記、必要なら長期抽出。
    - 出力: `{ message: string, usage?: {...}, memoryActions?: {...} }`
  - `GET /api/memory/short?date=YYYY-MM-DD`
  - `GET /api/memory/long`
  - （オプション）`GET /api/chat/stream`（SSE）

- エラーハンドリング/制御
  - OpenAI API 失敗時: リトライ（指数バックオフ）→ フォールバックメッセージ。
  - ツールのタイムアウト・I/O エラー時: ツール不使用で通常応答に切替。
  - 無毒化: プロンプトで安全方針を簡潔に付与。

### フロントエンド設計（TypeScript/React）

- 技術スタック
  - Vite + React + TypeScript
  - 状態管理は軽量（React 内部 state / Context）

- UI 仕様
  - 画面下部: 入力フィールド（送信ボタン/Enter送信）
  - 入力欄上: セッション内のメッセージリスト（ユーザー/AI の吹き出し）
  - 右側: キャラクター画像表示枠（将来的に動画/CGに拡張可）
  - 背景: `#A1C1E6`、テキスト: `#101010`

- API 通信
  - `POST /api/chat` を叩いて非ストリーム応答表示（初期）。
  - 将来: `EventSource` で `/api/chat/stream` を購読してストリーム表示。

- コンポーネント（例）
  - `ChatApp`（全体）
  - `MessageList`（メッセージ描画）
  - `Composer`（入力欄）
  - `SidePanel`（キャラクター画像）

- 型/モデル
  - `Message = { id: string, role: 'user'|'assistant', text: string, at: string }`
  - `ChatResponse = { message: string, usage?: any, memoryActions?: any }`

- スタイル
  - CSS 変数でカラー定義。レスポンシブ最適化は最小限。

### 実装スニペット（抜粋）

- Agents SDK: ツール定義とラン（概念例）
  ```python
  # backend/agent/character.py
  from agents import Agent, Runner, function_tool
  from . import runner as agent_runner
  from ..memory.manager import retrieve_texts, save_long_fact

  @function_tool
  def retrieve_memories(query: str | None = None, days: int | None = 14) -> str:
      return retrieve_texts(query=query, days=days)

  @function_tool
  def save_long_term_memory(text: str, category: str | None = None) -> str:
      return save_long_fact(text=text, category=category)

  def build_agent(model: str, instructions: str) -> Agent:
      return Agent(
          name="Assistant",
          instructions=instructions,
          model=model,
          tools=[retrieve_memories, save_long_term_memory],
      )

  async def run_turn(agent: Agent, user_text: str, session=None):
      # ツール呼び出しはエージェントの裁量（必要なときだけ思い出す）
      result = await Runner.run(agent, user_text, session=session)
      return result.final_output
  ```

- Responses API: 応答生成（メモリ結合後）
  ```python
  # backend/agent/runner.py
  from openai import OpenAI
  client = OpenAI()

  def complete_text(model: str, merged_text: str):
      resp = client.responses.create(model=model, input=merged_text)
      # response.output[*].content[*].text から本文抽出
      for item in (resp.output or []):
          if item.get("type") == "message":
              for part in item.get("content", []):
                  if part.get("type") == "output_text":
                      return part.get("text")
      return ""
  ```

- 短期→要約→削除のスケジュール実行
  ```python
  # backend/memory/summarizer.py
  from datetime import datetime, timedelta
  from .manager import list_short_files_due, summarize_to_3d, summarize_to_7d, purge_14d

  def daily_maintain():
      # 3日経過分
      for f in list_short_files_due(days=3):
          summarize_to_3d(f)
      # 7日経過分
      for f in list_short_files_due(days=7):
          summarize_to_7d(f)
      # 14日経過分
      for f in list_short_files_due(days=14):
          purge_14d(f)
  ```

### 運用・非機能

- ログ: API 呼び出し・ツール実行・ファイルI/O を INFO/DEBUG で記録。
- レート制御: 必要に応じて単純なリクエスト間隔制御を導入。
- 国際化: まず日本語優先。英語メッセージも最小限で併記可能。

### テスト計画（抜粋）

- ユニット: メモリ保存/読込、要約プロンプト、重複検知（指紋）。
- 結合: `POST /api/chat` が短期メモリに追記され、必要時に長期へ抽出されること。
- 疎通: OPENAI_API_KEY 未設定時の安全な失敗とエラーメッセージ。

### オープン事項（要確認）

1) バックエンドは `FastAPI` で問題ありませんか？（Flask等の希望があれば変更可）
2) ストリーミング（SSE/WebSocket）対応は初期から必要ですか？（非ストリームから開始可）
3) キャラクター画像の用意はありますか？（ダミー画像で開始も可）
4) メモリ格納先はリポジトリ直下 `./memory` で良いですか？（別パス希望があれば指定ください）
5) モデル名は既定 `gpt-5-mini` としますが、運用上は `OPENAI_MODEL` で上書きします。初期値はこれで良いですか？
