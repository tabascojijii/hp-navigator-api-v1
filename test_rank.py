import sqlite3

db = sqlite3.connect(r'c:\dev\hp-navigator-api\hp_akinator_prod.sqlite')
c = db.cursor()

def test_rank():
    q2 = '''
    SELECT t.title, f.rank as score
    FROM view_active_originals t
    JOIN tracks_fts f ON t.id = f.track_id
    WHERE f.semantic_tags MATCH 'semantic_tags:"16ビート" OR semantic_tags:"ロック"'
    ORDER BY f.rank
    LIMIT 10
    '''
    try:
        c.execute(q2)
        print("--- ORDER BY f.rank ---")
        for row in c.fetchall():
            print(row)
    except Exception as e:
        print("Error with f.rank:", e)

test_rank()
