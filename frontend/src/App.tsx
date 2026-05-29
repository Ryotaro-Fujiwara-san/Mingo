import { useState } from "react";
import MemoPanel from "./components/MemoPanel";
import HintButton from "./components/HintButton";
import "./App.css";

function App() {
  // 直近の会話の流れ。Step 1 の会話機能ができるまでは手入力で代用する。
  const [context, setContext] = useState("");

  return (
    <main className="app">
      <header className="app-header">
        <h1>Mingo — メモ &amp; ヒント</h1>
        <p className="subtitle">
          会話中に知らない表現をメモして、詰まったら「ヒント」で今使える表現を出す（Step 6）
        </p>
      </header>

      <div className="layout">
        <section className="col">
          <MemoPanel />
        </section>

        <section className="col">
          <h2>今の会話の流れ（仮入力）</h2>
          <p className="help">
            Step 1 の会話機能ができるまでは、ここに直近のやり取りを貼って動作確認できます。
          </p>
          <textarea
            className="context-input"
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="例: The interviewer just asked &quot;Why do you want to work here?&quot;"
            rows={5}
          />
          <HintButton context={context} />
        </section>
      </div>
    </main>
  );
}

export default App;
