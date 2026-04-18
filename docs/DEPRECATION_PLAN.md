# DEPRECATION PLAN (NO LEGACY PARALLEL RUN, AUDIT-REVISED)

## 1. 廃止する旧仕様一覧
- 無認証アクセス（全エンドポイント）
- Allowlist未適用アクセス
- `/health` の内部パス返却（`db` 実パス）
- 旧「互換期間あり」前提の運用

## 2. 廃止理由
- 認証・境界制御がない公開面を閉じるため。
  - 根拠: `C:\dev\hp-navigator-api\main.py`（認証実装なし）
- `/health` の情報露出を最小化するため。
  - 根拠: `C:\dev\hp-navigator-api\main.py:683`
- 単線切替で運用複雑性を下げるため。
  - 根拠: `C:\dev\hp-navigator-api\docs\IMPLEMENTATION_PLAN.md`

## 3. 廃止日（YYYY-MM-DD）
- 廃止日: `2026-05-15`
- タイムゾーン: `Asia/Tokyo`
- 方式: 同日一括切替（旧仕様の並行運用なし）

## 4. 影響範囲
- 認証なしでアクセスしている全クライアント
- `/health` の `db` 値に依存する監視ジョブ
- 許可CIDR未登録の運用ネットワーク

## 5. 代替手段
- `X-API-Key` + Allowlist 接続へ移行
- `/health` は `status` と `checks.db` のみ参照
- 契約正本:
  - `C:\dev\hp-navigator-api\docs\API_CONTRACT.md`

## 6. 切替当日Runbook（時刻入り）
### 6.1 事前（JST）
1. 09:00: 変更凍結開始、関係者へ最終告知
2. 09:30: `HP_SECURITY_ALLOWED_IPS` / `HP_SECURITY_TRUSTED_PROXY_CIDRS` 確認
3. 10:00: 監視系の `/health` 新契約への切替確認

### 6.2 切替（JST）
1. 10:30: 新版デプロイ開始
2. 10:40: ヘルス確認（内部のみ）
3. 10:45: 認証・403/401 レート確認
4. 11:00: Go/No-Go 判定

### 6.3 事後（JST）
1. 11:10: 旧仕様アクセス遮断確認
2. 11:30: 指標レビュー（2xx/4xx/5xx, p95, auth failure rate）
3. 12:00: 完了告知

## 7. Go/No-Go 判定条件
- Go条件:
  - 主要APIで 2xx 応答が期待通り
  - 401/403 が想定比率内
  - `/health` 監視が正常
  - p95 が目標範囲内（目標は `IMPLEMENTATION_PLAN.md`）
- No-Go条件:
  - 5xx が急増
  - 許可クライアントの多数が 403
  - 監視連続失敗

## 8. 切戻し判断条件
- 発動条件:
  - デプロイ後 15分以内に No-Go 条件を満たす
  - または運用責任者が重大障害と判断
- 手順:
  1. 直前安定リリースへロールバック
  2. インシデント記録開始
  3. 原因特定と再切替条件定義
- 注意:
  - 無認証恒久復帰は行わない（時間制限付き緩和のみ検討）

## 9. 運用告知項目
- 廃止日・時刻・タイムゾーン（JST）
- 必須ヘッダ `X-API-Key`
- IP許可ポリシーと trusted proxy 条件
- `/health` 返却項目変更
- エラー契約（400/401/403/422/500）
