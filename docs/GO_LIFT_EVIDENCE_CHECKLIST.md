# GO LIFT EVIDENCE CHECKLIST

## 1. 使い方
- 監査解除判定（CONDITIONAL GO 解除）時に本書を更新する。
- 各項目は `PASS | FAIL | PENDING` のいずれかで記録する。
- 証跡リンクは PR URL、CI URL、ログ保存先パスを記載する。

## 2. 解除条件チェック（機械判定向け）
| ID | 条件 | Status | Evidence | Reviewer | Reviewed At (JST) |
|---|---|---|---|---|---|
| GL-SEC-PR1 | PR1(request_id+共通エラー) 完了 | PENDING |  |  |  |
| GL-SEC-PR2 | PR2(API Key検証) 完了 | PENDING |  |  |  |
| GL-SEC-PR3 | PR3(trusted proxy+Allowlist) 完了 | PENDING |  |  |  |
| GL-SEC-PR4 | PR4(全endpoint適用+契約テスト) 完了 | PENDING |  |  |  |
| GL-CI-ERR | CIで 400/401/403/422/500 契約テスト成功 | PENDING |  |  |  |
| GL-HEALTH-ALLOW | `/health` 許可IPで 200 を実測 | PENDING |  |  |  |
| GL-HEALTH-DENY | `/health` 非許可IPで 403 を実測 | PENDING |  |  |  |
| GL-HEALTH-NOLEAK | `/health` に `db` 等内部情報が無い | PENDING |  |  |  |
| GL-AUDIT-LOG | 監査ログ必須キー出力を確認 | PENDING |  |  |  |
| GL-RUNBOOK-DRILL | Runbook演習(Go/No-Go/切戻し)完了 | PENDING |  |  |  |

## 3. 監査ログ必須キーサンプル（貼付欄）
- 必須キー:
  - `request_id`
  - `endpoint`
  - `method`
  - `status`
  - `client_ip`
  - `auth_result`
  - `api_key_id(masked)`
  - `reason`
  - `latency_ms`

```json
{
  "request_id": "req_sample",
  "endpoint": "/search",
  "method": "GET",
  "status": 403,
  "client_ip": "203.0.113.10",
  "auth_result": "deny_ip",
  "api_key_id(masked)": "key_prod_****9f2a",
  "reason": "ip_not_allowed",
  "latency_ms": 12
}
```

## 4. Go/No-Go 最終判定
- Go 判定条件:
  - 上表の `Status=PASS` が全件
  - `ROLL_OUT_RUNBOOK.md` の閾値を満たす
- No-Go 判定条件:
  - 上表に `FAIL` が1つでも存在
- 判定記録:
  - Decision:
  - IC:
  - API Owner:
  - Security Owner:
  - Timestamp (JST):

## 5. 関連ドキュメント
- `C:\dev\hp-navigator-api\docs\IMPLEMENTATION_PLAN.md`
- `C:\dev\hp-navigator-api\docs\SECURITY_IMPLEMENTATION_SPEC.md`
- `C:\dev\hp-navigator-api\docs\API_CONTRACT.md`
- `C:\dev\hp-navigator-api\docs\TEST_PLAN.md`
- `C:\dev\hp-navigator-api\docs\ROLL_OUT_RUNBOOK.md`

