# SECURITY IMPLEMENTATION SPEC

## 1. 目的
- 共通認証、IP判定、`request_id`、共通エラー契約を実装レベルで固定する。
- `/health` の情報露出を即時に抑止するためのアクセス制御を定義する。
- 根拠実装（現状）:
  - `C:\dev\hp-navigator-api\main.py:238`
  - `C:\dev\hp-navigator-api\main.py:331`
  - `C:\dev\hp-navigator-api\main.py:503`
  - `C:\dev\hp-navigator-api\main.py:676`
  - `C:\dev\hp-navigator-api\main.py:683`

## 2. 固定判定順序（必須）
1. `X-API-Key` 検証
  - 欠落/不正: `401 UNAUTHORIZED`
2. Client IP確定
  - trusted proxy 条件付きで `X-Forwarded-For` を解決
3. Allowlist判定
  - 非許可: `403 FORBIDDEN`

補足:
- 順序の入れ替えは禁止（401/403 の意味が崩れるため）。
- `request_id` は上記判定前に確定し、失敗レスポンスにも必ず付与する。

## 3. XFF解決アルゴリズム（疑似コード）
```text
input:
  remote_addr
  x_forwarded_for_header
  HP_SECURITY_TRUSTED_PROXY_CIDRS
  HP_SECURITY_ALLOWED_IPS

if remote_addr is invalid_ip:
  return 400 VALIDATION_ERROR(details.source="header", field="remote_addr")

if remote_addr in HP_SECURITY_TRUSTED_PROXY_CIDRS:
  if x_forwarded_for_header is missing or empty:
    return 400 VALIDATION_ERROR(details.source="header", field="X-Forwarded-For")
  leftmost = first_token(split_by_comma(x_forwarded_for_header)).trim()
  if leftmost is invalid_ip:
    return 400 VALIDATION_ERROR(details.source="header", field="X-Forwarded-For")
  client_ip = leftmost
else:
  client_ip = remote_addr

if client_ip not in HP_SECURITY_ALLOWED_IPS:
  return 403 FORBIDDEN

return client_ip
```

## 4. request_id 仕様
- 受信:
  - `X-Request-Id` が存在し、長さ `1..128` の可視ASCIIなら採用
  - それ以外は新規採番（UUIDv4推奨）
- 返却:
  - 全レスポンス（200/4xx/5xx）に `X-Request-Id` ヘッダを返却
- ログ:
  - すべての監査ログに `request_id` を必須含有

## 5. 共通エラー生成仕様
- 対象ステータス: `400/401/403/422/500`
- `error.code`:
  - `VALIDATION_ERROR`（400/422）
  - `UNAUTHORIZED`（401）
  - `FORBIDDEN`（403）
  - `INTERNAL_ERROR`（500）
- `VALIDATION_ERROR` 境界:
  - 400: ヘッダ/メタ情報
  - 422: query/body スキーマ/型
- `details.source` は固定値のみ許可:
  - `header | query | body`

## 6. 監査ログ必須キー
- `request_id`
- `endpoint`
- `method`
- `status`
- `client_ip`
- `auth_result`
- `api_key_id(masked)`
- `reason`
- `latency_ms`

`api_key_id(masked)` 例:
- `key_prod_****9f2a`

## 7. /health アクセス制御仕様
- `/health` は `HP_HEALTH_ALLOWED_IPS` で判定する。
- `/health` も `X-API-Key` 検証対象とする（運用例外なし）。
- `/health` レスポンスは最小セットのみ:
  - `status`
  - `timestamp`
  - `checks.db`
- 非返却:
  - `db` パス
  - 接続文字列
  - 内部設定値

## 8. 無効設定の扱い
- `HP_SECURITY_ALLOWED_IPS` / `HP_HEALTH_ALLOWED_IPS` / `HP_SECURITY_TRUSTED_PROXY_CIDRS` が不正CIDRを含む場合:
  - 起動失敗を標準とする（fail-closed）
  - 例外的に継続する運用は不可

## 9. 環境別固定方針
- local:
  - `HP_SECURITY_TRUSTED_PROXY_CIDRS` は未設定固定
  - `remote_addr` のみを client IP 判定に使用
- staging/prod:
  - `HP_SECURITY_TRUSTED_PROXY_CIDRS` 必須
  - trusted proxy 経由時のみ `X-Forwarded-For` を評価

## 10. `/health` 先行是正リリース方針
- `feature flag` は不採用（固定）
- 理由:
  - `/health` は内部専用で公開契約の影響面が限定的
  - 経路遮断 + 返却縮退 + テストで段階導入可能
- 反映順序:
  - `staging` 24時間観測後に `prod`
