// Mingo - メモ一覧・追加パネル
//
// 会話中に出会った知らない単語・表現を登録し、
// 自分専用の表現帳として管理する。

import { useEffect, useState, type FormEvent } from "react";
import { addMemo, deleteMemo, fetchMemos, type Memo } from "../api/client";

type Props = {
  // メモが変わったら親に知らせる（ヒントボタン側が最新メモを使えるように）
  onChange?: () => void;
};

export default function MemoPanel({ onChange }: Props) {
  const [memos, setMemos] = useState<Memo[]>([]);
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  async function reload() {
    try {
      setMemos(await fetchMemos());
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "読み込みに失敗しました");
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    try {
      await addMemo({ text, note });
      setText("");
      setNote("");
      await reload();
      onChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "追加に失敗しました");
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteMemo(id);
      await reload();
      onChange?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "削除に失敗しました");
    }
  }

  return (
    <div className="memo-panel">
      <h2>メモ（知らない単語・表現）</h2>

      <form onSubmit={handleAdd} className="memo-form">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="例: to be honest with you"
        />
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="意味・メモ（任意）"
        />
        <button type="submit">追加</button>
      </form>

      {error && <p className="error">{error}</p>}

      {memos.length === 0 ? (
        <p className="empty">まだメモがありません。</p>
      ) : (
        <ul className="memo-list">
          {memos.map((m) => (
            <li key={m.id}>
              <span className="memo-text">{m.text}</span>
              {m.note && <span className="memo-note"> — {m.note}</span>}
              <button
                type="button"
                className="memo-delete"
                onClick={() => handleDelete(m.id)}
                aria-label="削除"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
