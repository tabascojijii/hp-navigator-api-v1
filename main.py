"""
H!P-Navigator Backend API
SQLite3-native / FTS5-powered / Akinator engine
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List, Any
import sqlite3

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
DB_PATH = r"c:\dev\H!P-Akinator\data\export\hp_akinator_prod.sqlite"

# ---------------------------------------------------------------------------
# 起動時に DB 接続 & 閾値をメモリにロード
# ---------------------------------------------------------------------------
def _get_conn() -> sqlite3.Connection:
    """スレッドセーフなコネクションを返す (check_same_thread=False)"""
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

# グローバルコネクション & 閾値辞書
_con: sqlite3.Connection = _get_conn()

def _load_thresholds() -> dict[str, float]:
    cur = _con.cursor()
    cur.execute("SELECT score_name, threshold_value FROM meta_thresholds")
    return {row["score_name"]: row["threshold_value"] for row in cur.fetchall()}

THRESHOLDS: dict[str, float] = _load_thresholds()

# ---------------------------------------------------------------------------
# Pydantic モデル
# ---------------------------------------------------------------------------
class Answer(BaseModel):
    attribute: str   # era | is_tsunku | artist_name | tags
    operator: str    # == | contains
    value: Any

class AkinatorRequest(BaseModel):
    answers: List[Answer] = []
    step: int = 1

# ---------------------------------------------------------------------------
# FastAPI アプリ
# ---------------------------------------------------------------------------
app = FastAPI(
    title="H!P-Navigator Backend API",
    description="SQLite3 / FTS5 powered search & Akinator engine for Hello! Project songs",
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# ヘルパー: Row → dict
# ---------------------------------------------------------------------------
def _rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# /search エンドポイント
# ---------------------------------------------------------------------------
@app.get("/search")
def search(
    q:       Optional[str] = Query(None, description="キーワード（曲名・アーティスト名）"),
    tag:     Optional[str] = Query(None, description="セマンティックタグ（FTS5 MATCH）"),
    fame:    Optional[str] = Query(None, description="知名度 (standard | hidden | manic)"),
    mood:    Optional[str] = Query(None, description="感情スコアキー (euphoria, sentimental, … )"),
    bpm_min: Optional[int] = Query(None, description="最小BPM (tempo)"),
    bpm_max: Optional[int] = Query(None, description="最大BPM (tempo)"),
):
    clauses: list[str] = []
    params:  list[Any] = []

    # ---- キーワード検索 (title / artist_name) ----
    if q:
        clauses.append("(title LIKE ? OR artist_name LIKE ?)")
        wildcard = f"%{q}%"
        params += [wildcard, wildcard]

    # ---- タグ検索 (FTS5 MATCH) ----
    if tag:
        clauses.append(
            "id IN (SELECT track_id FROM tracks_fts WHERE tracks_fts MATCH ?)"
        )
        params.append(f'semantic_tags:"{tag}"')

    # ---- 知名度フィルタ ----
    if fame == "standard":
        clauses.append("fame_score >= 0.3")
    elif fame == "hidden":
        clauses.append("fame_score >= 0.1 AND fame_score < 0.4")
    elif fame == "manic":
        clauses.append("fame_score < 0.1")

    # ---- ムードフィルタ ----
    if mood:
        col = f"score_{mood}"
        if mood == "graduation":
            # 卒業曲特例: 閾値テーブル無視 / score > 0.7 OR FTS5 MATCH 卒業曲
            clauses.append(
                "(score_graduation > 0.7 OR id IN "
                "(SELECT track_id FROM tracks_fts WHERE tracks_fts MATCH ?))"
            )
            params.append('semantic_tags:"卒業曲"')
        elif col in THRESHOLDS:
            clauses.append(f"{col} >= ?")
            params.append(THRESHOLDS[col])

    # ---- BPM フィルタ ----
    if bpm_min is not None:
        clauses.append("tempo >= ?")
        params.append(bpm_min)
    if bpm_max is not None:
        clauses.append("tempo <= ?")
        params.append(bpm_max)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"""
        SELECT *
        FROM view_active_originals
        {where}
        ORDER BY RANDOM()
        LIMIT 3
    """
    cur = _con.cursor()
    cur.execute(sql, params)
    return _rows_to_dicts(cur.fetchall())


# ---------------------------------------------------------------------------
# /akinator エンドポイント (SQL-only Akinator エンジン)
# ---------------------------------------------------------------------------
@app.post("/akinator")
def run_akinator(request: AkinatorRequest):
    # ---- Step 1: 履歴に基づく WHERE 句の構築 ----
    clauses: list[str] = []
    params:  list[Any] = []

    for ans in request.answers:
        attr = ans.attribute
        op   = ans.operator
        val  = ans.value

        if attr == "tags":
            # タグは FTS5 サブクエリ
            if op == "==":
                clauses.append(
                    "id IN (SELECT track_id FROM tracks_fts WHERE tracks_fts MATCH ?)"
                )
                params.append(f'semantic_tags:"{val}"')
            elif op == "!=":
                clauses.append(
                    "id NOT IN (SELECT track_id FROM tracks_fts WHERE tracks_fts MATCH ?)"
                )
                params.append(f'semantic_tags:"{val}"')
        elif attr == "artist_name":
            if op == "==":
                clauses.append("artist_name = ?")
                params.append(val)
            elif op == "!=":
                clauses.append("artist_name != ?")
                params.append(val)
        elif attr == "era":
            if op == "==":
                clauses.append("era = ?")
                params.append(val)
            elif op == "!=":
                clauses.append("era != ?")
                params.append(val)
        elif attr == "is_tsunku":
            clauses.append("is_tsunku = ?")
            params.append(1 if val else 0)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    cur = _con.cursor()

    # ---- Step 2: 残件数 ----
    cur.execute(f"SELECT COUNT(*) FROM view_active_originals {where}", params)
    remaining_count: int = cur.fetchone()[0]

    # ---- Step 3: 終了判定 ----
    if remaining_count <= 3 or request.step >= 15:
        if remaining_count == 0:
            return {"status": "finished", "remaining_count": 0, "songs": []}
        cur.execute(
            f"SELECT * FROM view_active_originals {where} ORDER BY RANDOM() LIMIT 3",
            params,
        )
        return {
            "status": "finished",
            "remaining_count": remaining_count,
            "songs": _rows_to_dicts(cur.fetchall()),
        }

    # ---- Step 4: 次問の選定 (0.5 に最も近い分割比のカラムを SQL で集計) ----
    used_attrs = {ans.attribute for ans in request.answers}

    best_diff = float("inf")
    best_question: dict | None = None

    def _check(diff: float, question: dict):
        nonlocal best_diff, best_question
        if diff < best_diff:
            best_diff = diff
            best_question = question

    # 候補 A: era (まだ質問していない場合)
    if "era" not in used_attrs:
        cur.execute(
            f"""
            SELECT era, COUNT(*) as cnt
            FROM view_active_originals {where}
            GROUP BY era
            ORDER BY cnt DESC
            LIMIT 1
            """,
            params,
        )
        row = cur.fetchone()
        if row and row["cnt"] > 0:
            p = row["cnt"] / remaining_count
            _check(abs(p - 0.5), {"attribute": "era", "operator": "==", "value": row["era"]})

    # 候補 B: is_tsunku (まだ質問していない場合)
    if "is_tsunku" not in used_attrs:
        cur.execute(
            f"SELECT SUM(is_tsunku) as cnt_1 FROM view_active_originals {where}",
            params,
        )
        row = cur.fetchone()
        if row and row["cnt_1"] is not None:
            p = row["cnt_1"] / remaining_count
            _check(abs(p - 0.5), {"attribute": "is_tsunku", "operator": "==", "value": True})

    # 候補 C: artist_name (最頻アーティストで分割)
    if "artist_name" not in used_attrs:
        used_artists = [a.value for a in request.answers if a.attribute == "artist_name"]
        exclude_sql = ""
        ex_params = list(params)
        if used_artists:
            placeholders = ",".join("?" * len(used_artists))
            exclude_sql = f" AND artist_name NOT IN ({placeholders})"
            ex_params += used_artists
        cur.execute(
            f"""
            SELECT artist_name, COUNT(*) as cnt
            FROM view_active_originals {where} {exclude_sql}
            GROUP BY artist_name
            ORDER BY ABS(CAST(COUNT(*) AS REAL) / {remaining_count} - 0.5)
            LIMIT 1
            """,
            ex_params,
        )
        row = cur.fetchone()
        if row and row["cnt"] > 0:
            p = row["cnt"] / remaining_count
            _check(abs(p - 0.5), {"attribute": "artist_name", "operator": "==", "value": row["artist_name"]})

    # 候補 D: tags (FTS5 で頻出タグを集計)
    if "tags" not in used_attrs:
        used_tags = [a.value for a in request.answers if a.attribute == "tags"]
        cur.execute(
            f"SELECT semantic_tags FROM view_active_originals {where}",
            params,
        )
        tag_counts: dict[str, int] = {}
        for row in cur.fetchall():
            raw = row["semantic_tags"] or ""
            for t in (x.strip() for x in raw.split(",") if x.strip()):
                if t not in used_tags:
                    tag_counts[t] = tag_counts.get(t, 0) + 1

        if tag_counts:
            best_tag = min(tag_counts, key=lambda t: abs(tag_counts[t] / remaining_count - 0.5))
            p = tag_counts[best_tag] / remaining_count
            _check(abs(p - 0.5), {"attribute": "tags", "operator": "==", "value": best_tag})

    # フォールバック
    if not best_question:
        cur.execute(
            f"SELECT title FROM view_active_originals {where} LIMIT 1",
            params,
        )
        row = cur.fetchone()
        best_question = {
            "attribute": "title",
            "operator": "==",
            "value": row["title"] if row else "不明",
        }

    return {
        "status": "questioning",
        "remaining_count": remaining_count,
        "next_question": best_question,
    }


# ---------------------------------------------------------------------------
# /concierge エンドポイント (ガイド付き検索)
# ---------------------------------------------------------------------------
@app.get("/concierge")
def concierge(
    q:       Optional[str] = Query(None),
    tag:     Optional[str] = Query(None),
    fame:    Optional[str] = Query(None),
    mood:    Optional[str] = Query(None),
    bpm_min: Optional[int] = Query(None),
    bpm_max: Optional[int] = Query(None),
    step:    int           = Query(1, description="現在の質問ステップ数"),
):
    clauses: list[str] = []
    params:  list[Any] = []

    if q:
        clauses.append("(title LIKE ? OR artist_name LIKE ?)")
        wildcard = f"%{q}%"
        params += [wildcard, wildcard]

    if tag:
        clauses.append(
            "id IN (SELECT track_id FROM tracks_fts WHERE tracks_fts MATCH ?)"
        )
        params.append(f'semantic_tags:"{tag}"')

    if fame == "standard":
        clauses.append("fame_score >= 0.3")
    elif fame == "hidden":
        clauses.append("fame_score >= 0.1 AND fame_score < 0.4")
    elif fame == "manic":
        clauses.append("fame_score < 0.1")

    if mood:
        col = f"score_{mood}"
        if mood == "graduation":
            clauses.append(
                "(score_graduation > 0.7 OR id IN "
                "(SELECT track_id FROM tracks_fts WHERE tracks_fts MATCH ?))"
            )
            params.append('semantic_tags:"卒業曲"')
        elif col in THRESHOLDS:
            clauses.append(f"{col} >= ?")
            params.append(THRESHOLDS[col])

    if bpm_min is not None:
        clauses.append("tempo >= ?")
        params.append(bpm_min)
    if bpm_max is not None:
        clauses.append("tempo <= ?")
        params.append(bpm_max)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cur = _con.cursor()

    cur.execute(f"SELECT COUNT(*) FROM view_active_originals {where}", params)
    remaining_count: int = cur.fetchone()[0]

    if remaining_count <= 20 or step >= 5:
        if remaining_count == 0:
            return {"status": "finished", "remaining_count": 0, "songs": []}
        cur.execute(
            f"SELECT * FROM view_active_originals {where} ORDER BY RANDOM() LIMIT 3",
            params,
        )
        return {
            "status": "finished",
            "remaining_count": remaining_count,
            "songs": _rows_to_dicts(cur.fetchall()),
        }

    # ヒント生成: 頻出タグを SQL 集計
    cur.execute(
        f"SELECT semantic_tags FROM view_active_originals {where} LIMIT 200",
        params,
    )
    tag_counts: dict[str, int] = {}
    for row in cur.fetchall():
        raw = row["semantic_tags"] or ""
        for t in (x.strip() for x in raw.split(",") if x.strip()):
            if not tag or t.lower() != tag.lower():
                tag_counts[t] = tag_counts.get(t, 0) + 1

    if tag_counts:
        top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:3]
        hint = {"attribute": "tag", "options": top_tags}
    else:
        hint = {"attribute": "mood", "options": ["euphoria", "sentimental", "struggle"]}

    return {
        "status": "questioning",
        "remaining_count": remaining_count,
        "next_hints": hint,
    }
