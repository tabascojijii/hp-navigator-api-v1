# API CONTRACT (NEW, NON-LEGACY, AUDIT-REVISED)

## 1. 共通方針
- 旧互換は前提にしない。
- 認証:
  - `X-API-Key` 必須
  - IP Allowlist 必須
- `X-Request-Id`:
  - リクエストで受信した場合はその値を採用
  - 未指定時はサーバー採番し、レスポンスヘッダ `X-Request-Id` で返却
- 共通エラーHTTPステータス:
  - `400 Bad Request`
  - `401 Unauthorized`
  - `403 Forbidden`
  - `422 Unprocessable Entity`
  - `500 Internal Server Error`
- 根拠実装（現状エンドポイント）:
  - `C:\dev\hp-navigator-api\main.py:238`
  - `C:\dev\hp-navigator-api\main.py:331`
  - `C:\dev\hp-navigator-api\main.py:503`
  - `C:\dev\hp-navigator-api\main.py:676`

## 2. IP判定・Allowlist契約
- 判定優先順位:
  1. `remote_addr` が `HP_SECURITY_TRUSTED_PROXY_CIDRS` に含まれる場合のみ `X-Forwarded-For` を信頼
  2. それ以外は `remote_addr` を使用
- `X-Forwarded-For`:
  - 左端IPをクライアントIPとして採用
  - パース不能/形式不正/空文字は `400`（`VALIDATION_ERROR`）
  - 採用IPがAllowlist外は `403`（`FORBIDDEN`）
- 設定キー:
  - `HP_SECURITY_ALLOWED_IPS`
  - `HP_SECURITY_TRUSTED_PROXY_CIDRS`
  - `HP_HEALTH_ALLOWED_IPS`

## 3. 共通エラースキーマ（監査対応）
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "API key is missing or invalid.",
    "request_id": "req_01HXYZ...",
    "details": {
      "field": "X-API-Key"
    }
  }
}
```

- `error.code`: `UNAUTHORIZED | FORBIDDEN | VALIDATION_ERROR | INTERNAL_ERROR`
- `error.message`: 人間可読の短文
- `error.request_id`: 追跡用ID
- `error.details`: 任意（検証エラー等の補足）
- `VALIDATION_ERROR` のステータス境界:
  - `400`: HTTPヘッダ/メタ情報の不正（例: 不正 `X-Forwarded-For`）
  - `422`: リクエストボディ/クエリの型・スキーマ不正
  - どちらも `error.code=VALIDATION_ERROR` を利用し、`details.source` で区別（`header` or `body`）

### 3.1 400例
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid X-Forwarded-For header.",
    "request_id": "req_400_sample",
    "details": {
      "source": "header",
      "field": "X-Forwarded-For",
      "reason": "invalid ip format"
    }
  }
}
```

### 3.2 401例
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "API key is missing or invalid.",
    "request_id": "req_401_sample"
  }
}
```

### 3.3 403例
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Client IP is not allowed.",
    "request_id": "req_403_sample",
    "details": {
      "client_ip": "203.0.113.10"
    }
  }
}
```

### 3.4 422例
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "request_id": "req_422_sample",
    "details": {
      "source": "body",
      "field": "step",
      "reason": "must be integer"
    }
  }
}
```

### 3.5 500例
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred.",
    "request_id": "req_500_sample"
  }
}
```

## 4. GET /search
### Request (Query)
- `q` (string, optional)
- `tag` (string, optional)
- `fame` (string, optional): `standard | hidden | manic`
- `mood` (string, optional)
- `bpm_min` (integer, optional)
- `bpm_max` (integer, optional)

### Response 200
```json
[
  {
    "id": "trk_xxx",
    "title": "sample title",
    "artist_name": "sample artist",
    "semantic_tags": "EDM,16ビート",
    "tempo": 132.0,
    "fame_score": 0.41
  }
]
```

### Error
- `400/401/403/422/500`

## 5. POST /akinator
### Request
```json
{
  "answers": [
    { "attribute": "era", "operator": "==", "value": "2010s" }
  ],
  "step": 3
}
```

### Response 200 (questioning)
```json
{
  "status": "questioning",
  "remaining_count": 128,
  "next_question": {
    "attribute": "is_tsunku",
    "operator": "==",
    "value": true
  }
}
```

### Response 200 (finished)
```json
{
  "status": "finished",
  "remaining_count": 2,
  "songs": [
    { "id": "trk_a", "title": "song a", "artist_name": "artist a" }
  ]
}
```

### ルール固定値
- `HP_RULE_AKINATOR_FINISH_REMAINING_MAX`（初期値 3）
- `HP_RULE_AKINATOR_FINISH_STEP_MAX`（初期値 15）
- 根拠: `C:\dev\hp-navigator-api\main.py:350`

### Error
- `400/401/403/422/500`

## 6. GET /concierge
### Request (Query)
- `q` (string, optional)
- `tag` (string, optional)
- `fame` (string, optional)
- `mood` (string, optional)
- `bpm_min` (integer, optional)
- `bpm_max` (integer, optional)
- `step` (integer, optional, default 1)

### Response 200 (questioning)
```json
{
  "status": "questioning",
  "remaining_count": 67,
  "next_hints": {
    "attribute": "tag",
    "options": ["ライブ定番", "16ビート", "ロック"]
  }
}
```

### Response 200 (finished)
```json
{
  "status": "finished",
  "remaining_count": 12,
  "songs": [
    { "id": "trk_c", "title": "song c", "artist_name": "artist c" }
  ]
}
```

### ルール固定値
- `HP_RULE_CONCIERGE_FINISH_REMAINING_MAX`（初期値 20）
- `HP_RULE_CONCIERGE_FINISH_STEP_MAX`（初期値 5）
- 根拠: `C:\dev\hp-navigator-api\main.py:595`

### Error
- `400/401/403/422/500`

## 7. GET /health（内部専用）
### 公開方針
- 外部公開しない
- OpenAPIに含めない
- `HP_HEALTH_ALLOWED_IPS` で到達制御

### Response 200
```json
{
  "status": "ok",
  "timestamp": "2026-04-18T22:00:00Z",
  "checks": {
    "db": "ok"
  }
}
```

### 非返却
- DBパス等の内部情報
- 接続文字列等の機密情報

### Error
- `400/401/403/422/500`
