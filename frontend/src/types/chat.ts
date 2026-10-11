export type MessageRole = "user" | "assistant";

/** One SOAI knowledge base passage used for an answer (backend: metadata.sources). */
export interface Source {
  id: string;
  title: string;
  section?: string;
  source?: string;
  similarity?: number;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  /** RAG answers: the knowledge base passages used. */
  sources?: Source[];
  /** Tool answers: calculator, weather, datetime... */
  tool?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  updatedAt: Date;
}
