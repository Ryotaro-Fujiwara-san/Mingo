// Mingo frontend - バックエンドAPI呼び出し
//
// 開発中は backend が http://localhost:8000 で動いている前提。
// 本番URLは frontend/.env の VITE_API_BASE で差し替え可能。

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

// ── 型定義（backend が返す JSON の形）──
export type Memo = {
  id: string;
  text: string;
  note: string;
  source: string;
  created_at: string;
};

export type HintSuggestion = {
  id: string;
  text: string;
  example: string;
  reason: string;
};

// レスポンスを共通処理する。失敗時は backend の detail を Error にして投げる。
async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // JSON でないエラー応答は無視
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ── メモ ──
export async function fetchMemos(): Promise<Memo[]> {
  const res = await fetch(`${API_BASE}/api/memo`);
  const data = await handle<{ memos: Memo[] }>(res);
  return data.memos;
}

export async function addMemo(input: {
  text: string;
  note?: string;
  source?: string;
}): Promise<Memo> {
  const res = await fetch(`${API_BASE}/api/memo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handle<Memo>(res);
}

export async function deleteMemo(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/memo/${id}`, { method: "DELETE" });
  await handle<{ deleted: string }>(res);
}

// ── ヒント ──
export async function fetchHints(
  context: string,
  max = 3,
): Promise<HintSuggestion[]> {
  const res = await fetch(`${API_BASE}/api/expression_hint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ context, max }),
  });
  const data = await handle<{ suggestions: HintSuggestion[] }>(res);
  return data.suggestions;
}
