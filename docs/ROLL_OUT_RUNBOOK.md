# ROLL OUT RUNBOOK (Asia/Tokyo)

## 1. 対象
- セキュリティ境界の本番切替:
  - `X-API-Key` 必須化
  - IP Allowlist 適用
  - `/health` 縮退レスポンス化
- 関連仕様:
  - `C:\dev\hp-navigator-api\docs\SECURITY_IMPLEMENTATION_SPEC.md`
  - `C:\dev\hp-navigator-api\docs\API_CONTRACT.md`
  - `C:\dev\hp-navigator-api\docs\GO_LIFT_EVIDENCE_CHECKLIST.md`

## 1.1 `/health` 先行是正 PR 適用順
1. staging へ先行適用
2. 24時間観測（内部200/外部403/非返却）
3. 問題なければ prod 反映
4. 失敗時は先行是正PRのみ切戻し（他PRへ波及させない）

## 2. 役割
- Incident Commander (IC): 全体判断、Go/No-Go 最終承認
- API Owner: 契約整合、デプロイ承認
- SRE On-Call: デプロイ実行、監視確認、切戻し実行
- Security Owner: キー/Allowlist妥当性確認
- Communications: 告知、障害連絡

## 3. 当日手順（JST）
### 3.1 事前
1. 09:00 変更凍結開始
2. 09:10 `HP_API_KEYS` の有効性確認
3. 09:20 `HP_SECURITY_ALLOWED_IPS` / `HP_HEALTH_ALLOWED_IPS` / `HP_SECURITY_TRUSTED_PROXY_CIDRS` 構文確認
4. 09:40 監視ダッシュボード準備（2xx/4xx/5xx, p95, auth failure）
5. 10:00 Go判定前レビュー

### 3.2 デプロイ
1. 10:30 デプロイ開始
2. 10:35 `/health` 内部疎通確認（許可IPのみ）
3. 10:40 API疎通（有効キー + 許可IP）
4. 10:45 エラー比率とレイテンシ観測
5. 11:00 Go/No-Go 判定

### 3.3 事後
1. 11:05 告知（Go/No-Go 結果）
2. 11:20 15分観測結果レビュー
3. 12:00 切替完了宣言

## 4. Go/No-Go 判定閾値（数値）
- Go条件（全て満たす）:
  - 5xx rate < 1.0%
  - p95 latency:
    - `/search`, `/concierge` <= 300ms
    - `/akinator` <= 500ms
  - auth failure rate（401+403） <= 5.0%（想定クライアント切替済み前提）
  - `/health`:
    - 許可IPで 200
    - 非許可IPで 403
    - `db` など内部情報が返らない
- No-Go条件（1つでも該当）:
  - 5xx rate >= 2.0% が連続5分
  - 許可クライアントで 403 が 10%以上
  - `/health` が外部IPから到達可能
  - `/health` レスポンスに `db` または内部設定値が含まれる

## 5. 切戻し条件と担当ロール
- 切戻し条件:
  - No-Go条件の該当
  - IC または SRE On-Call が重大影響と判断
- 担当:
  - 実行: SRE On-Call
  - 承認: IC + API Owner
  - 告知: Communications
  - 判定記録: Security Owner（証跡チェックリスト更新）
- 切戻し手順:
  1. 直前安定版へロールバック
  2. 監視安定化確認（15分）
  3. インシデント記録と再発防止策の起票
  4. `GO_LIFT_EVIDENCE_CHECKLIST.md` に No-Go 理由を記録

## 6. インシデント初動テンプレ
```text
[Incident Title]
Security rollout degradation - YYYY-MM-DD HH:mm JST

[Impact]
- affected endpoints:
- user impact:
- start time:

[Current Metrics]
- 5xx rate:
- auth failure rate:
- p95 latency:
- health exposure check:

[Decision]
- Go / No-Go:
- rollback: yes/no
- owner:

[Next Update ETA]
- HH:mm JST
```

## 7. 演習証跡の保存ルール
- 保存先（絶対パス）:
  - `C:\dev\hp-navigator-api\docs\evidence\`
- ファイル命名:
  - `RUNBOOK_DRILL_YYYY-MM-DD.md`
- 必須メタ情報:
  - Ticket ID
  - Minutes ID
  - 実施日時（JST）
  - 実施者（氏名）
