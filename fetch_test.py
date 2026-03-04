import urllib.request
import urllib.parse
import json

url = "http://localhost:8000/concierge?" + urllib.parse.urlencode({
    "tag": "16ビート クール ロック ダンス 赤羽橋ファンク EDM",
    "step": 5
})

req = urllib.request.Request(url)
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read().decode("utf-8"))

print(f"ヒット数: {data['remaining_count']}")
for s in data['songs']:
    print(f"- 曲名: {s['title']}")
    print(f"  タグ: {s.get('semantic_tags', '')}")
