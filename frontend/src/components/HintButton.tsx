// Mingo - ヒントボタン
//
// 自分の発話ターン中に押すと、メモ済み表現の中から
// 「今の文脈で使えるもの」を GPT がサジェストする。
// 考え込んで黙ってしまう（フリーズ）のを防ぐのが狙い。

import { useState } from "react";
import { fetchHints, type HintSuggestion } from "../api/client";

type Props = {
  // 直近の会話の流れ。Step 1 の会話実装が入るまでは手入力で渡す。
  context: string;
};

export default function HintButton({ context }: Props) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<HintSuggestion[]>([]);
  const [error, setError] = useState("");
  const [asked, setAsked] = useState(false);

  async function handleClick() {
    setLoading(true);
    setError("");
    setAsked(true);
    try {
      setSuggestions(await fetchHints(context, 3));
    } catch (e) {
      setError(e instanceof Error ? e.message : "ヒント取得に失敗しました");
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="hint">
      <button
        type="button"
        className="hint-button"
        onClick={handleClick}
        disabled={loading}
      >
        {loading ? "考え中…" : "💡 ヒント"}
      </button>

      {error && <p className="error">{error}</p>}

      {asked && !loading && !error && suggestions.length === 0 && (
        <p className="empty">今の文脈で使えそうなメモは見つかりませんでした。</p>
      )}

      {suggestions.length > 0 && (
        <ul className="hint-list">
          {suggestions.map((s) => (
            <li key={s.id}>
              <strong>{s.text}</strong>
              <div className="hint-example">“{s.example}”</div>
              {s.reason && <div className="hint-reason">{s.reason}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
