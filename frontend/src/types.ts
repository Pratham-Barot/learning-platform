export interface User {
  id: number;
  email: string;
  full_name: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export type SourceType = "youtube" | "document" | "web";

export type OutputLanguage = "en" | "hi";

export const OUTPUT_LANGUAGE_OPTIONS: {
  value: OutputLanguage;
  label: string;
}[] = [
  { value: "en", label: "English" },
  { value: "hi", label: "Hindi (हिन्दी)" },
];

export interface SessionSummary {
  id: number;
  title: string;
  source_type: string;
  source_ref: string | null;
  created_at: string;
}

export interface SessionDetail extends SessionSummary {
  notes: string;
  quiz: QuizQuestion[];
  content_difficulty: string | null;
  output_language?: OutputLanguage | string | null;
}

export interface QuizQuestion {
  question: string;
  options: string[];
  answer: string;
  explanation: string;
  topic?: string;
  difficulty?: string;
}

export interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  step: string | null;
  error: string | null;
  session_id: number | null;
}

export interface ChatMessage {
  id: number;
  role: string;
  content: string;
  source_label: string | null;
  created_at: string;
}

export interface QuizResult {
  question_index: number;
  question: string;
  user_answer: string | null;
  correct_answer: string;
  explanation: string;
  is_correct: boolean;
  topic?: string | null;
  difficulty?: string | null;
}

export interface QuizSubmitResponse {
  score: number;
  total: number;
  results: QuizResult[];
  weak_topics: string[];
  should_practice: boolean;
  practice_generated: boolean;
  practice_quiz: QuizQuestion[] | null;
  practice_error: string | null;
}

export interface AdaptiveQuizResponse {
  quiz: QuizQuestion[];
  question_count: number;
}
