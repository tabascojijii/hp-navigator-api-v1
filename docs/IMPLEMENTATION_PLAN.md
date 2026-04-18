# IMPLEMENTATION PLAN (NON-LEGACY, AUDIT-REVISED)

## 1. 目的
- 旧 `main.py` モノリスを分割し、新契約APIへ安全に置き換える。
- 旧レガシー互換は維持しない。切替は単線で実施する。
- 本書は実装前の承認基準であり、承認後に実装へ進む。

## 2. 非互換前提の新スコープ
- 対象:
  - `GET /search`
  - `POST /akinator`
  - `GET /concierge`
  - `GET /health`（内部監視専用）
  - API / Service / DB 分離
  - 認証・公開境界・エラー契約の固定
- 非対象:
  - UI刷新
  - 旧クライアント向け並行運用
  - 大規模アルゴリズム再発明

## 3. 現状監査（事実）
- API/業務ロジック/SQLが単一ファイルに密結合。
  - 根拠: `C:\dev\hp-navigator-api\main.py`
- 主要4エンドポイントが直接DBを扱う。
  - 根拠: `C:\dev\hp-navigator-api\main.py:238`, `:331`, `:503`, `:676`
- ランダム依存クエリが複数あり、再現性を下げる。
  - 根拠: `C:\dev\hp-navigator-api\main.py:295`, `:316`, `:322`, `:604`, `:609`, `:618`
- 終了条件がコード直書き。
  - 根拠: `C:\dev\hp-navigator-api\main.py:350`, `:595`
- `/health` は OpenAPI非掲載だが内部パス返却あり。
  - 根拠: `C:\dev\hp-navigator-api\main.py:676`, `:683`

## 4. アーキテクチャ方針（API/Service/DB）
- API層:
  - 認証、IP判定、バリデーション、エラーマッピング、`request_id` 付与。
- Service層:
  - `/search` `/akinator` `/concierge` の業務ルール実装。
  - 終了条件は設定値参照（定数直書き禁止）。
- DB層:
  - 接続管理、SQL実行、行変換、DB例外の正規化。
  - API層から直接SQLを実行しない。

## 5. セキュリティ方針
### 5.1 採用方式
- 採用: `API Key + IP Allowlist`
- 理由:
  - 最小実装で公開境界を即時に閉じられる。
  - 現行構成からの移行差分が小さい。

### 5.2 IP Allowlist 判定基準（監査対応）
- 判定IPソース優先順位:
  1. 接続元IP（`remote_addr`）が信頼済みリバースプロキシCIDRに含まれる場合のみ `X-Forwarded-For` を採用
  2. それ以外は `remote_addr` を採用
- `X-Forwarded-For` 取り扱い:
  - カンマ区切りの左端IPをクライアントIPとして採用
  - 不正ヘッダ（空、パース不能、IP形式不正）は `400`（`VALIDATION_ERROR`）で拒否
  - 採用IPが Allowlist 外の場合は `403`（`FORBIDDEN`）
- 設定キー:
  - `HP_SECURITY_ALLOWED_IPS`
  - `HP_SECURITY_TRUSTED_PROXY_CIDRS`
  - `HP_HEALTH_ALLOWED_IPS`
- 環境差分方針:
  - local: `HP_SECURITY_TRUSTED_PROXY_CIDRS` は未設定とする（ローカルは reverse proxy 非経由を標準運用）
  - staging/prod: `HP_SECURITY_TRUSTED_PROXY_CIDRS` 必須
  - prod では private CIDR の網羅確認をリリースゲート化
- 実装詳細の正本:
  - `C:\dev\hp-navigator-api\docs\SECURITY_IMPLEMENTATION_SPEC.md`
  - 固定順序: `X-API-Key検証 -> Client IP確定 -> Allowlist判定`

### 5.3 APIキー運用（追加改善）
- ローテーション周期: 90日
- 漏えい疑い時フロー:
  1. 該当キーを即時失効
  2. 代替キー発行
  3. 影響期間ログを監査
  4. 再発防止策を記録
- Allowlist更新承認フロー:
  1. 申請（理由・CIDR・期限）
  2. APIオーナー承認
  3. 変更実施
  4. 監査ログ記録

## 6. /health 契約再定義
- 外部公開しない（内部監視専用）。
- OpenAPIに含めない（`include_in_schema=False` 維持）。
- 返却項目は最小化し、内部パスを返さない。
- 許可IPは `HP_HEALTH_ALLOWED_IPS` を使用。

### 6.1 `/health` 先行是正計画（High Blocker対応）
- 目的:
  - 既存 `db` パス露出を最短で解消する。
  - 根拠: `C:\dev\hp-navigator-api\main.py:683`
- 手順:
  1. レスポンスを最小セットへ縮退（`status`, `timestamp`, `checks.db`）
  2. `/health` を `HP_HEALTH_ALLOWED_IPS` で到達制御
  3. 非許可経路は `403` を返却
  4. 非返却項目（`db`, 接続文字列, 内部設定値）を契約固定
- 先行リリース可否:
  - 可（`/health` は OpenAPI非掲載・内部用途のため独立先行対象）
  - `feature flag` は不採用（方針固定）。理由: 経路制御と契約縮退のみのため構成複雑化を避ける。
- 反映順序:
  - `staging` で 24時間観測後、`prod` に反映
- 外部経路遮断の運用:
  - WAF/Ingress/Proxy で `/health` を内部ネットワークに限定
  - API層でも `HP_HEALTH_ALLOWED_IPS` で二重防御
- 検証項目:
  - 内部許可IP: 200
  - 非許可IP: 403
  - レスポンスに `db` 等が存在しない
- 失敗時切戻し条件:
  - staging/prod で `/health` 許可IPが 200 を返せない
  - 非許可IPで 403 が出ない
  - レスポンスに `db` または内部設定値が含まれる

## 7. 終了条件・業務ルール固定
- `/akinator`:
  - `remaining_count <= HP_RULE_AKINATOR_FINISH_REMAINING_MAX`（初期値 3）
  - `step >= HP_RULE_AKINATOR_FINISH_STEP_MAX`（初期値 15）
- `/concierge`:
  - `remaining_count <= HP_RULE_CONCIERGE_FINISH_REMAINING_MAX`（初期値 20）
  - `step >= HP_RULE_CONCIERGE_FINISH_STEP_MAX`（初期値 5）
- 根拠（現状値）:
  - `C:\dev\hp-navigator-api\main.py:350`, `:595`
- 変更承認フロー:
  1. 変更理由と影響範囲を記述
  2. テスト結果を添付
  3. APIオーナー承認
  4. 契約書とOpenAPIを同時更新

## 8. 設定値命名規約（監査対応）
- 規約:
  - `HP_API_*`（API契約・識別）
  - `HP_SECURITY_*`（認証/境界）
  - `HP_RULE_*`（業務ルール）
  - `HP_HEALTH_*`（ヘルス用途）
- 本計画で使用するキー:
  - `HP_API_KEYS`
  - `HP_SECURITY_ALLOWED_IPS`
  - `HP_SECURITY_TRUSTED_PROXY_CIDRS`
  - `HP_RULE_AKINATOR_FINISH_REMAINING_MAX`
  - `HP_RULE_AKINATOR_FINISH_STEP_MAX`
  - `HP_RULE_CONCIERGE_FINISH_REMAINING_MAX`
  - `HP_RULE_CONCIERGE_FINISH_STEP_MAX`
  - `HP_HEALTH_ALLOWED_IPS`

## 9. 非機能要件（最小定義）
- レイテンシ目標（推定）:
  - `/search`, `/concierge`: p95 <= 300ms
  - `/akinator`: p95 <= 500ms
- タイムアウト:
  - アプリ内処理タイムアウト 2s
  - 上流プロキシタイムアウト 5s
- 最大同時接続（推定）:
  - 50 同時リクエストを基準負荷とする
- 可用性目標（簡易）:
  - 月間 99.5%

## 10. 観測性（Observability）
- `X-Request-Id` 方針:
  - 受信時にあれば採用
  - なければサーバーで採番し、レスポンスヘッダへ返却
- 構造化ログ必須項目:
  - `request_id`, `endpoint`, `status`, `latency_ms`
- 最低限メトリクス:
  - `2xx/4xx/5xx` 件数
  - p95 レイテンシ
  - auth failure rate（401/403 比率）

## 11. OpenAPI/契約同期ルール（追加改善）
- 契約変更時は `docs/API_CONTRACT.md` と OpenAPI を同一PRで同時更新する。
- PRレビューで「契約差分チェック」を必須化する。
- `/health` は OpenAPI 管理対象外とする（内部監視専用）。
- `/health` の契約正本は `docs/API_CONTRACT.md` とし、PRで差分レビューを必須化する。
- `/health` 変更時は `docs/API_CONTRACT.md` とテストケース更新（`docs/TEST_PLAN.md` 準拠）を同一PRで必須化する。
- チェック対象:
  - path/method
  - request schema
  - response schema
  - error schema

## 12. 実装ステップ（時系列）
1. セキュリティ仕様固定（`SECURITY_IMPLEMENTATION_SPEC.md`）
2. `/health` 先行是正（内部専用・最小返却）
3. 契約固定（API_CONTRACT + OpenAPI）
4. セキュリティ実装（API Key + Allowlist + IP判定規則）
5. 層分離（API/Service/DB）
6. テスト実装（unit + integration）
7. 単線切替（旧仕様停止）
8. 運用告知・監視確認

### 12.1 セキュリティ層 PR分割計画（固定）
- PR1: `request_id` + 共通エラーハンドラ
  - DoD:
    - 全レスポンスで `X-Request-Id` を返却
    - 400/401/403/422/500 が共通エラースキーマ準拠
    - `API_CONTRACT.md` と `TEST_PLAN.md` の契約テスト追加済み
- PR2: API Key 検証
  - DoD:
    - `X-API-Key` 欠落/不正で 401
    - 正常キーで後続判定へ進む
    - 監査ログに `auth_result` と `api_key_id(masked)` を出力
- PR3: trusted proxy 判定 + Allowlist
  - DoD:
    - `remote_addr` / `X-Forwarded-For` 解決が `SECURITY_IMPLEMENTATION_SPEC.md` 準拠
    - Allowlist 非許可で 403
    - 無効CIDR設定で fail-closed（起動失敗）
- PR4: 全エンドポイント適用 + 契約テスト
  - DoD:
    - `/search`, `/akinator`, `/concierge`, `/health` すべてで共通セキュリティ層有効
    - `/health` 先行是正チェック（内部200/外部403/非返却）合格
    - `GO_LIFT_EVIDENCE_CHECKLIST.md` の必須証跡を全添付

### 12.2 リリースゲート（数値固定）
- 判定指標:
  - auth failure rate（401+403） <= 5.0%
  - 5xx rate < 1.0%（No-Go: >= 2.0% が連続5分）
  - p95 latency:
    - `/search`, `/concierge` <= 300ms
    - `/akinator` <= 500ms
- 責任者:
  - 判定責任: Incident Commander (IC)
  - 技術承認: API Owner
  - セキュリティ承認: Security Owner
- 証跡正本:
  - `C:\dev\hp-navigator-api\docs\ROLL_OUT_RUNBOOK.md`
  - `C:\dev\hp-navigator-api\docs\GO_LIFT_EVIDENCE_CHECKLIST.md`

## 13. リスクと対策
- 外部設定（Custom GPT Actions）未回収
  - 対策: 切替前に必須項目を棚卸し
- XFF誤判定による誤遮断
  - 対策: stagingで trusted proxy 検証を必須化
- ランダム依存による flaky
  - 対策: TEST_PLANの2層戦略を適用

## 14. Definition of Done
- 監査4点が文書とテスト計画に反映済み
- 新契約とOpenAPIが一致
- `/health` が内部専用・最小返却
- セキュリティ運用（ローテーション/失効/承認）がRunbook化

## 15. ロールバック
- 原則: 直前リリースへ即時ロールバック
- 判定: 401/403急増、5xx増加、可用性低下
- 無認証恒久復帰は不可
