import type { ExamplesResponse, RagResult } from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export async function getExamples(): Promise<ExamplesResponse> {
  const res = await fetch(`${API_URL}/api/examples`);
  if (!res.ok) throw new Error(`Could not load examples (${res.status})`);
  return res.json();
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
