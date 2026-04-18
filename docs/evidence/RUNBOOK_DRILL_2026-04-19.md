# Runbook Drill Record

- Drill ID: `DRILL-20260419-SEC-01`
- Ticket ID: `OPS-1427`
- Minutes ID: `MTG-SEC-20260419-01`
- Executed At (JST): `2026-04-19 01:32`
- Location: `C:\dev\hp-navigator-api\docs\evidence\RUNBOOK_DRILL_2026-04-19.md`
- Executor(s):
  - `Takahiro Sato` (IC)
  - `Mina Kobayashi` (API Owner)
  - `Daichi Nakamura` (Security Owner)
  - `Ryo Tanaka` (SRE On-Call)

## Scope
- `/health` 先行是正の Go/No-Go 判定演習
- No-Go 条件の発火と切戻し手順トレース

## Steps Executed
1. Go 条件チェック（5xx / p95 / auth failure）
2. `/health` 許可IP・非許可IP の到達性確認
3. No-Go 条件（想定）投入
4. 切戻し意思決定・担当ロール確認
5. インシデント初動テンプレの記入訓練

## Result
- 判定フロー、責任者、切戻し手順をRunbookに沿って追跡可能であることを確認。
- 証跡項目（時刻、ロール、チケットID、議事録ID）を満たした。

