import httpx

#テスト用に入れる表現
memos = [
    # --- 週末の活動系（クエリに関連） ---
    "hang out with friends",
    "go hiking",
    "get some rest",
    "grab a coffee",
    "watch a movie",
    "sleep in",
    "do the laundry",
    "go shopping",
    "visit my parents",
    "play video games",
    "cook dinner",
    "read a novel",
    "go for a run",
    "clean the house",
    "take a nap",
    # --- 無関係系（precisionのテスト用） ---
    "submit a report",
    "book a flight",
    "fix a bug",
    "attend a meeting",
    "pay the rent",
    "sign a contract",
    "water the plants",
    "renew my passport",
    "file taxes",
    "charge my phone",
]
for m in memos:
    r = httpx.post("http://localhost:8000/memo", json={"text": m}, timeout=60)
   