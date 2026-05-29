# Mingo backend - メモ機能 + ヒント生成 (Step 6)
#
# やること:
#   1) 会話中に出会った単語・表現を「メモ」として保存する（自分専用の表現帳）
#   2) 発話に詰まったとき、メモ済み表現から「今の文脈で使えるもの」をサジェスト
#
# メモの保存先は backend/cache/memos.json（DB はフェーズ2で導入）。
# ヒント生成は OpenAI Chat Completions を使う。

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ────────────────────────────────────────────────
# メモの保存場所（backend/cache/memos.json）
# ────────────────────────────────────────────────
CACHE_DIR = Path(__file__).parent / "cache"
MEMO_FILE = CACHE_DIR / "memos.json"


def _load() -> list[dict]:
    """JSON ファイルから全メモを読み込む。無ければ空リストを返す。"""
    if not MEMO_FILE.exists():
        return []
    try:
        return json.loads(MEMO_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # 壊れていたら空扱いにして落とさない
        return []


def _save(memos: list[dict]) -> None:
    """全メモを JSON ファイルへ書き込む。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MEMO_FILE.write_text(
        json.dumps(memos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ────────────────────────────────────────────────
# メモの CRUD（一覧・追加・削除）
# ────────────────────────────────────────────────
def list_memos() -> list[dict]:
    """新しい順にメモを返す。"""
    return sorted(_load(), key=lambda m: m["created_at"], reverse=True)


def add_memo(text: str, note: str = "", source: str = "") -> dict:
    """メモを 1 件追加して、追加したメモを返す。

    text   : 覚えたい単語・表現（必須）
    note   : 意味やメモ書き（任意）
    source : どこで出会ったか（"ai" / "self" など、任意）
    """
    memos = _load()
    memo = {
        "id": uuid.uuid4().hex,
        "text": text.strip(),
        "note": note.strip(),
        "source": source.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    memos.append(memo)
    _save(memos)
    return memo


def delete_memo(memo_id: str) -> bool:
    """指定 ID のメモを削除。削除できたら True、無ければ False。"""
    memos = _load()
    remaining = [m for m in memos if m["id"] != memo_id]
    if len(remaining) == len(memos):
        return False
    _save(remaining)
    return True


# ────────────────────────────────────────────────
# ヒント生成（メモ済み表現から今の文脈で使えるものを選ぶ）
# ────────────────────────────────────────────────
# 仕様書では "GPT-5" 表記。実際に叩くモデル名は環境変数で差し替え可能。
#   例: backend/.env に  OPENAI_MODEL=gpt-5  と書けばそれを使う。
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_SYSTEM_PROMPT = """You are an English speaking coach inside a live conversation app.
The learner is a Japanese speaker practicing English. They sometimes freeze and
cannot recall expressions they have saved. Given (1) the recent conversation
context and (2) a list of expressions the learner has saved, pick the ones the
learner could naturally use RIGHT NOW to keep talking.

Rules:
- Only choose expressions from the provided list. Never invent new ones.
- Prefer expressions that fit the current context naturally.
- For each chosen expression, write ONE short, natural example sentence the
  learner could actually say next, in English.
- Add a very short reason in Japanese (なぜ今使えるか).
- Return STRICT JSON in this shape:
  {"suggestions": [{"id": "...", "text": "...", "example": "...", "reason": "..."}]}
- If nothing fits, return {"suggestions": []}."""


class MissingAPIKey(RuntimeError):
    """OPENAI_API_KEY が未設定のときに送出する。"""


def suggest_hints(context: str, max_n: int = 3) -> list[dict]:
    """直近の会話文脈 context を渡し、メモ済み表現から使えるものを返す。

    戻り値: [{"id", "text", "example", "reason"}, ...]
    """
    memos = list_memos()
    if not memos:
        return []

    if not os.getenv("OPENAI_API_KEY"):
        raise MissingAPIKey(
            "OPENAI_API_KEY が未設定です。backend/.env に設定してください。"
        )

    # キーが無い環境でも import 自体は通るよう、ここで遅延 import する
    from openai import OpenAI

    client = OpenAI()

    memo_lines = "\n".join(
        f'- id={m["id"]} | "{m["text"]}"'
        + (f' (意味: {m["note"]})' if m["note"] else "")
        for m in memos
    )
    user_prompt = (
        f"Recent conversation context:\n{context.strip() or '(no context yet)'}\n\n"
        f"Saved expressions:\n{memo_lines}\n\n"
        f"Choose up to {max_n} expressions."
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    # モデルが実在しない id を返すことがあるので、実在するメモだけに絞る
    valid_ids = {m["id"] for m in memos}
    cleaned: list[dict] = []
    for s in data.get("suggestions", [])[:max_n]:
        if isinstance(s, dict) and s.get("id") in valid_ids:
            cleaned.append(
                {
                    "id": s["id"],
                    "text": s.get("text", ""),
                    "example": s.get("example", ""),
                    "reason": s.get("reason", ""),
                }
            )
    return cleaned
