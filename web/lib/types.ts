// Mirrors the backend Pydantic models (monitoring_guide.models).

export interface Chunk {
  id: string;
  doc_id: string;
  index: number;
  text: string;
}

export interface RetrievedChunk {
  chunk: Chunk;
  score: number;
}

export interface Citation {
  chunk_id: string;
  quote: string;
}

export interface Answer {
  answer: string;
  abstained: boolean;
  citations: Citation[];
}

export interface RagResult {
  query: string;
  answer: Answer;
  retrieved: RetrievedChunk[];
}

export interface ExamplesResponse {
  examples: string[];
  disclaimer: string;
}
