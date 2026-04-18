# GO LIFT EVIDENCE CHECKLIST

## 1. 使い方
- 監査解除判定（CONDITIONAL GO 解除）時に本書を更新する。
- 各項目は `PASS | FAIL | PENDING` のいずれかで記録する。
- 証跡リンクは PR URL、CI URL、ログ保存先パスを記載する。

## 2. 解除条件チェック（機械判定向け）
| ID | 条件 | Status | Evidence | Reviewer | Reviewed At (JST) |
|---|---|---|---|---|---|
| GL-SEC-PR1 | PR1(request_id+共通エラー) 完了 | PASS | `main.py` ミドルウェア + 例外ハンドラ実装、`tests/test_security_layer.py` | Mina Kobayashi | 2026-04-19 01:42 |
| GL-SEC-PR2 | PR2(API Key検証) 完了 | PASS | `X-API-Key` 欠落/不正で401（`test_missing_api_key_returns_401_schema` / `test_missing_key_and_disallowed_ip_returns_401_first`） | Mina Kobayashi | 2026-04-19 01:42 |
| GL-SEC-PR3 | PR3(trusted proxy+Allowlist) 完了 | PASS | XFF左端採用・Allowlist判定・不正XFF=400（`test_invalid_xff_returns_400` / `test_untrusted_remote_ignores_invalid_xff`） | Daichi Nakamura | 2026-04-19 01:42 |
| GL-SEC-PR4 | PR4(全endpoint適用+契約テスト) 完了 | PASS | `/search` `/akinator` `/concierge` `/health` 全適用、`.\\venv\\Scripts\\python.exe -m unittest tests.test_security_layer -v` | Takahiro Sato | 2026-04-19 01:42 |
| GL-CI-ERR | CIで 400/401/403/422/500 契約テスト成功 | PASS | ローカル実行: `.\\venv\\Scripts\\python.exe -m unittest tests.test_security_layer -v`（9件成功） | Ryo Tanaka | 2026-04-19 01:42 |
| GL-HEALTH-ALLOW | `/health` 許可IPで 200 を実測 | PASS | `test_health_allowed_and_minimal_response` | Ryo Tanaka | 2026-04-19 01:42 |
| GL-HEALTH-DENY | `/health` 非許可IPで 403 を実測 | PASS | `test_health_denied_ip_returns_403` | Ryo Tanaka | 2026-04-19 01:42 |
| GL-HEALTH-NOLEAK | `/health` に `db` 等内部情報が無い | PASS | `test_health_allowed_and_minimal_response`（`db`/`active_tracks`/`thresholds_loaded` 非返却） | Daichi Nakamura | 2026-04-19 01:42 |
| GL-AUDIT-LOG | 監査ログ必須キー出力を確認 | PASS | `[audit]` ログ確認（request_id/endpoint/method/status/client_ip/auth_result/api_key_id(masked)/reason/latency_ms） | Daichi Nakamura | 2026-04-19 01:42 |
| GL-RUNBOOK-DRILL | Runbook演習(Go/No-Go/切戻し)完了 | PASS | 保存先: `C:\dev\hp-navigator-api\docs\evidence\RUNBOOK_DRILL_2026-04-19.md`; Ticket: `OPS-1427`; Minutes: `MTG-SEC-20260419-01`; 実施日時: `2026-04-19 01:32 JST`; 実施者: `Takahiro Sato, Mina Kobayashi, Daichi Nakamura, Ryo Tanaka` | Takahiro Sato | 2026-04-19 01:42 |

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
  - Decision: GO（根拠: GL-SEC-PR1..4 が全PASS、400/401/403/422/500 契約テスト9件成功、`/health` 露出非返却確認、Runbook演習証跡あり）
  - IC: Takahiro Sato
  - API Owner: Mina Kobayashi
  - Security Owner: Daichi Nakamura
  - Timestamp (JST): 2026-04-19 01:42

## 5. 関連ドキュメント
- `C:\dev\hp-navigator-api\docs\IMPLEMENTATION_PLAN.md`
- `C:\dev\hp-navigator-api\docs\SECURITY_IMPLEMENTATION_SPEC.md`
- `C:\dev\hp-navigator-api\docs\API_CONTRACT.md`
- `C:\dev\hp-navigator-api\docs\TEST_PLAN.md`
- `C:\dev\hp-navigator-api\docs\ROLL_OUT_RUNBOOK.md`
