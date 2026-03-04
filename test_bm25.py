import sqlite3

db = sqlite3.connect(r'c:\dev\hp-navigator-api\hp_akinator_prod.sqlite')
c = db.cursor()

def test_bm25():
    q = '''
    SELECT t.title, bm25(tracks_fts) as score
    FROM view_active_originals t
    JOIN tracks_fts f ON t.id = f.track_id
    WHERE tracks_fts MATCH 'semantic_tags:"16ビート" OR semantic_tags:"ロック"'
    ORDER BY bm25(tracks_fts)
    LIMIT 10
    '''
    try:
        c.execute(q)
        for row in c.fetchall():
            print(row)
    except Exception as e:
        print("Error with tracks_fts:", e)

    q2 = '''
    SELECT t.title, bm25(f) as score
    FROM view_active_originals t
    JOIN tracks_fts f ON t.id = f.track_id
    WHERE f MATCH 'semantic_tags:"16ビート" OR semantic_tags:"ロック"'
    ORDER BY bm25(f)
    LIMIT 10
    '''
    try:
        c.execute(q2)
        print("-------------")
        for row in c.fetchall():
            print(row)
    except Exception as e:
        print("Error with f alias:", e)


test_bm25()
