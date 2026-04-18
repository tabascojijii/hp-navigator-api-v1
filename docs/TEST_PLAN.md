# TEST PLAN (AUDIT-REVISED)

## 1. テスト対象一覧
- `GET /search`
- `POST /akinator`
- `GET /concierge`
- `GET /health`（内部専用）
- 認証/境界:
  - `X-API-Key`
  - IP Allowlist（`remote_addr` / `X-Forwarded-For`）
- エラー契約:
  - 400/401/403/422/500 のボディ形式
- 業務ルール:
  - Akinator/Concierge の終了条件設定値
- 監査ログ:
  - 必須キー出力の検証

## 2. 2層テスト戦略（監査対応）
### 2.1 Unit Test（モック中心）
- 目的:
  - 分岐、状態遷移、エラーマッピングを決定的に検証
- 対象:
  - 認証判定
  - IP抽出ルール
  - 終了条件の境界値
  - エラースキーマ整形
- 方針:
  - DBアクセスをモックし、ランダム分岐を固定入力で検証

### 2.2 Integration Test（固定fixture SQLite）
- 目的:
  - 実SQLとレスポンス契約を実データで検証
- 対象:
  - `/search` のFTS・フォールバック
  - `/akinator` と `/concierge` の終了分岐
  - `/health` の内部専用契約（`docs/API_CONTRACT.md` を正本として検証）
- fixture方針:
  - 最小件数: 30曲以上（推定: 分岐網羅に必要）
  - カバレッジ意図:
    - 複数 `era`
    - `is_tsunku` の 0/1
    - 複数 `fame_score` 帯
    - `semantic_tags` の重複/希少タグ
    - `tempo` の上下限
- 根拠（現行SQL分岐）:
  - `C:\dev\hp-navigator-api\main.py:295`, `:316`, `:322`, `:350`, `:595`, `:604`, `:609`, `:618`

## 3. ランダム挙動対策（監査対応）
- `ORDER BY RANDOM()` 結果は「内容完全一致」を検証しない。
- 検証項目:
  - 件数上限を満たすこと（例: <= 3）
  - 必須キーが存在すること（`id`, `title`, `artist_name` 等）
  - 結果行が検索条件を満たすこと（または仕様上のフォールバック条件を満たすこと）
- Unitで分岐ロジック、IntegrationでSQL妥当性を分離して保証。

## 4. エラーボディ契約テスト（監査対応）
- 対象ステータス: 400/401/403/422/500
- 必須検証:
  - `error.code`
  - `error.message`
  - `error.request_id`
  - `error.details`（必要時のみ）
- 境界検証:
  - ヘッダ/メタ情報の不正は 400（`details.source=header`）
  - クエリの型・スキーマ不正は 422（`details.source=query`）
  - ボディの型・スキーマ不正は 422（`details.source=body`）
- 契約正本:
  - `C:\dev\hp-navigator-api\docs\API_CONTRACT.md`

## 5. 必須自動テストケース
### 5.1 認証/認可
- APIキー欠落で 401（`UNAUTHORIZED`）
- 不正APIキーで 401（`UNAUTHORIZED`）
- Allowlist外で 403（`FORBIDDEN`）

### 5.2 IP抽出
- trusted proxy 配下で `X-Forwarded-For` 左端IP採用
- trusted proxy 外で `remote_addr` 採用
- 不正XFFで 400（`VALIDATION_ERROR`）
- 不正XFF時は `details.source=header` を検証
- 無効CIDR設定時は起動失敗（fail-closed）を検証

### 5.3 /search
- 200 + 配列形式
- 入力型不正で 422
- フォールバック時も件数上限とスキーマ維持
- `bpm_min > bpm_max` で 422（`details.source=query`）
- 異常長 `q`（上限超過）で 422（`details.source=query`）

### 5.4 /akinator
- `questioning` で `next_question`
- `finished` で `songs`
- 終了条件境界値の検証
- `step` 型不正で 422（`details.source=body`）
- `step <= 0` で 422（`details.source=body`）

### 5.5 /concierge
- `questioning` で `next_hints`
- `finished` で `songs`
- 終了条件境界値の検証
- `step` 型不正で 422（`details.source=body`）
- `step <= 0` で 422（`details.source=query`）

### 5.6 /health
- 許可条件で 200
- 非許可条件で 403
- 内部情報非返却
- 非返却項目検証: `db`, `db_path`, `connection_string`, `thresholds_loaded` が存在しない

### 5.7 監査ログ検証
- 必須キーが出力されること:
  - `request_id`, `endpoint`, `method`, `status`
  - `client_ip`, `auth_result`, `api_key_id(masked)`, `reason`
  - `latency_ms`
- 401/403/400 系でも `request_id` と `reason` が出力されること

## 6. CI実行基準・再実行ポリシー（監査対応）
- PRごとに unit + integration を自動実行
- flaky疑い時の再実行:
  - 自動再試行 2回（合計最大3実行）
  - 3回中1回でも失敗が残る場合は失敗扱い
- 失敗時の扱い:
  - ランダム依存ケースは修正完了までマージ禁止
  - 原因と対策をPRに記録
- 解除条件証跡:
  - `C:\dev\hp-navigator-api\docs\GO_LIFT_EVIDENCE_CHECKLIST.md` の CI欄を同一PRで更新

## 7. 完了判定
- `API_CONTRACT.md` との契約一致テストが全件成功
- 400/401/403/422/500 のエラーボディ契約が全件成功
- ランダム依存の flaky が CI上で収束
- `/health` 契約検証（内部200/外部403/非返却）が成功
