import { FALLBACK_DISCLAIMER, FALLBACK_EXAMPLES } from "./samples";
import type { Example, ExamplesResponse, RagResult } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

// Never rejects: falls back to the baked-in examples when the API is cold or the
// response isn't the expected shape, so "Load example" always works.
export async function getExamples(): Promise<ExamplesResponse> {
  try {
    const res = await fetch(`${API_URL}/api/examples`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    const body = await res.json();
    const ok =
      Array.isArray(body?.examples) &&
      body.examples.length > 0 &&
      body.examples.every((e: Example) => typeof e?.text === "string" && typeof e?.label === "string");
    if (!ok) throw new Error("unexpected examples shape");
    return body as ExamplesResponse;
  } catch {
    return { examples: FALLBACK_EXAMPLES, disclaimer: FALLBACK_DISCLAIMER };
  }
}

export async function ask(question: string): Promise<RagResult> {
  const res = await fetch(`${API_URL}/api/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON */
    }
    throw new Error(detail);
  }
  return res.json();
}
