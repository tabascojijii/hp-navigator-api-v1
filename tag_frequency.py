import sqlite3
import os
from collections import Counter

db_path = os.path.join(r"c:\dev\hp-navigator-api", "hp_akinator_prod.sqlite")
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute("SELECT semantic_tags FROM view_active_originals WHERE semantic_tags IS NOT NULL")
rows = c.fetchall()

all_tags = []
for row in rows:
    tags = [t.strip() for t in row[0].split(",") if t.strip()]
    all_tags.extend(tags)

tag_counts = Counter(all_tags)
top_30 = tag_counts.most_common(30)

print("=== 出現頻度ランキング TOP 30 ===")
for i, (tag, count) in enumerate(top_30, 1):
    print(f"{i:2d}. {tag} ({count}件)")

# カテゴリ別のキーワード（部分一致でカウント）
categories = {
    "ハイテンション/盛り上がる系": ["ライブ定番", "アンセム", "盛り上がる", "ハイテンション", "アゲアゲ", "アップテンポ", "パーティー", "コール", "楽しい"],
    "エモい/泣ける系": ["切ない", "センチメンタル", "泣ける", "エモい", "バラード", "ミディアム", "メッセージ", "失恋", "青春"],
    "カッコいい/クール系": ["16ビート", "ファンク", "EDM", "クール", "カッコいい", "ダンス", "バキバキ", "ロック", "ディスコ"],
    "個性的/ハロプロ特有": ["トンチキ", "つんく♂イズム", "台詞入り", "変拍子", "コミカル", "寸劇", "ハロプロらしい"]
}

print("\n=== ジャンル別関連タグのヒット数（概算） ===")
for cat_name, keywords in categories.items():
    print(f"\n[{cat_name}]")
    total_for_cat = 0
    cat_counts = {}
    for tag, count in tag_counts.items():
        if any(kw in tag for kw in keywords):
            cat_counts[tag] = count
            total_for_cat += count
            
    # そのカテゴリ内で上位5つを表示
    sorted_cat = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for tag, count in sorted_cat:
        print(f"  - {tag}: {count}件")
    print(f"  >> 合計(タグ数の累計): {total_for_cat}件程度")

conn.close()
