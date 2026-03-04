import sqlite3
import os

db_path = os.path.join(r"c:\dev\hp-navigator-api", "hp_akinator_prod.sqlite")
conn = sqlite3.connect(db_path)
c = conn.cursor()

def check(match_str):
    q = "SELECT count(*) FROM view_active_originals WHERE id IN (SELECT track_id FROM tracks_fts WHERE semantic_tags MATCH ?)"
    try:
        c.execute(q, (match_str,))
        return c.fetchone()[0]
    except Exception as e:
        return str(e)

print('赤羽橋ファンク:', check('semantic_tags:"赤羽橋ファンク"'))
print('16ビート:', check('semantic_tags:"16ビート"'))
print('グルーブ感:', check('semantic_tags:"グルーブ感"'))
print('AND explicit:', check('semantic_tags:("赤羽橋ファンク" AND "16ビート" AND "グルーブ感")'))
print('OR explicit:', check('semantic_tags:("赤羽橋ファンク" OR "16ビート" OR "グルーブ感")'))
print('フレーズ検索:', check('semantic_tags:"赤羽橋ファンク 16ビート グルーブ感"'))
