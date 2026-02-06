export type ResearchStatus =
  | "planning"
  | "awaiting_approval"
  | "running"
  | "completed"
  | "failed";

export type ResearchSource = {
  url: string;
  title?: string;
  snippet?: string;
  retrieved_at?: string;
  file_id?: string;
  notes?: string;
};

export type ResearchArtifact = {
  file_id: string;
  name: string;
  kind: "pdf" | "html" | "text";
  created_at?: string;
  source_url?: string;
};

export type ResearchPlan = {
  clarifying_questions: string[];
  expanded_queries: string[];
  outline: string[];
};

export type ResearchSession = {
  research_id: string;
  created_at: string;
  updated_at: string;
  status: ResearchStatus;
  initial_query: string;
  plan: ResearchPlan;
  report_markdown: string;
  sources: ResearchSource[];
  artifacts: ResearchArtifact[];
};

