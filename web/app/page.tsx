"use client";

import { useEffect, useState } from "react";
import { ask, getExamples } from "../lib/api";
import type { RagResult } from "../lib/types";

export default function Home() {
  const [q, setQ] = useState("");
  const [examples, setExamples] = useState<string[]>([]);
  const [disclaimer, setDisclaimer] = useState("");
  const [result, setResult] = useState<RagResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getExamples()
      .then((r) => { setExamples(r.examples); setDisclaimer(r.disclaimer); })
      .catch(() => { /* examples are optional */ });
  }, []);

  async function run(question: string) {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setResult(await ask(question));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  const a = result?.answer;

  return (
    <div className="container">
      <header>
        <h1>monitoring-guide</h1>
        <p>Cited Q&amp;A over illustrative drug/condition monitoring guidance — it abstains when the corpus doesn&rsquo;t cover your question.</p>
      </header>

      <div className="banner">
        ⚠️ Demo / educational. Answers come only from a small illustrative corpus paraphrased from
        public guidance — <strong>not clinical advice</strong>, and not a substitute for current guidance.
      </div>

      <label htmlFor="q">Your monitoring question</label>
      <input
        id="q"
        type="text"
        value={q}
        placeholder="e.g. What monitoring does a patient on lithium need?"
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && run(q)}
      />
      <div className="actions">
        <button onClick={() => run(q)} disabled={loading}>{loading ? "Searching…" : "Ask"}</button>
      </div>

      {examples.length > 0 && (
        <div className="examples">
          {examples.map((ex) => (
            <span className="chip" key={ex} onClick={() => { setQ(ex); run(ex); }}>{ex}</span>
          ))}
        </div>
      )}

      {error && <div className="error">{error}</div>}

      {a && (
        <div className="panel">
          <span className={`badge ${a.abstained ? "abstained" : "answered"}`}>
            {a.abstained ? "Not covered — abstained" : "Answered from guidance"}
          </span>
          <div className="answer">{a.answer}</div>
          {a.citations.length > 0 && (
            <>
              <h3 style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.04em", margin: "14px 0 8px" }}>Citations</h3>
              {a.citations.map((c, i) => (
                <div className="cite" key={i}>
                  <div className="id">{c.chunk_id}</div>
                  <div className="q">“{c.quote}”</div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {disclaimer && <p className="disc">{disclaimer}</p>}
    </div>
  );
}
