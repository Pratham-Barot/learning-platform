import type {
  AdaptiveQuizResponse,
  AuthResponse,
  ChatMessage,
  JobStatus,
  QuizSubmitResponse,
  SessionDetail,
  SessionSummary,
  SourceType,
  User,
} from "../types";
import { clearAuth, getToken, saveAuth } from "../auth/storage";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: authHeaders(options?.headers),
    });
  } catch {
    throw new Error(
      "Cannot reach the server. Make sure the backend is running on port 8000.",
    );
  }

  if (response.status === 401) {
    clearAuth();
    window.location.reload();
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      detail = await response.text();
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json() as Promise<T>;
}

export async function registerUser(payload: {
  email: string;
  password: string;
  fullName?: string;
}): Promise<User> {
  const data = await request<AuthResponse>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      full_name: payload.fullName,
    }),
  });
  saveAuth(data.access_token, data.user);
  return data.user;
}

export async function loginUser(email: string, password: string): Promise<User> {
  const data = await request<AuthResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  saveAuth(data.access_token, data.user);
  return data.user;
}

export async function fetchMe(): Promise<User> {
  return request<User>("/api/auth/me");
}

export async function fetchSessions(): Promise<SessionSummary[]> {
  return request<SessionSummary[]>("/api/sessions");
}

export async function fetchSession(id: number): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/sessions/${id}`);
}

export async function deleteSession(id: number): Promise<void> {
  await request(`/api/sessions/${id}`, { method: "DELETE" });
}

export async function renameSession(id: number, title: string): Promise<SessionSummary> {
  return request<SessionSummary>(`/api/sessions/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function startGenerate(params: {
  sourceType: SourceType;
  youtubeUrl?: string;
  webUrl?: string;
  file?: File;
  outputLanguage?: string;
}): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("source_type", params.sourceType);
  form.append("output_language", params.outputLanguage || "en");
  if (params.youtubeUrl) form.append("youtube_url", params.youtubeUrl);
  if (params.webUrl) form.append("web_url", params.webUrl);
  if (params.file) form.append("file", params.file);

  return request<{ job_id: string }>("/api/generate", {
    method: "POST",
    body: form,
  });
}

export async function fetchJobStatus(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/api/generate/${jobId}/status`);
}

export async function fetchChatHistory(sessionId: number): Promise<ChatMessage[]> {
  return request<ChatMessage[]>(`/api/sessions/${sessionId}/chat`);
}

export async function submitQuiz(
  sessionId: number,
  answers: Record<string, string>,
  autoPractice = true,
): Promise<QuizSubmitResponse> {
  return request<QuizSubmitResponse>(`/api/sessions/${sessionId}/quiz/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, auto_practice: autoPractice }),
  });
}

export async function generateAdaptiveQuiz(
  sessionId: number,
  weakTopics: string[],
  missedQuestions: string[] = [],
): Promise<AdaptiveQuizResponse> {
  return request<AdaptiveQuizResponse>(`/api/sessions/${sessionId}/quiz/adaptive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      weak_topics: weakTopics,
      missed_questions: missedQuestions,
    }),
  });
}

export async function downloadPdf(sessionId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/pdf`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error("PDF download failed");

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "study_notes_and_quiz.pdf";
  link.click();
  URL.revokeObjectURL(url);
}

export async function streamChat(
  sessionId: number,
  message: string,
  onToken: (text: string) => void,
  onDone: (payload: { source: string; content: string }) => void,
  onError: (error: Error) => void,
  editMessageId?: number,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/sessions/${sessionId}/chat/stream`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        message,
        edit_message_id: editMessageId ?? null,
      }),
    });
  } catch {
    onError(new Error("Cannot reach the server. Is the backend running?"));
    return;
  }

  if (response.status === 401) {
    clearAuth();
    window.location.reload();
    return;
  }

  if (!response.ok || !response.body) {
    let detail = "Chat request failed";
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    onError(new Error(typeof detail === "string" ? detail : "Chat request failed"));
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data: ")) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "token") onToken(payload.text);
        if (payload.type === "done") {
          finished = true;
          onDone(payload);
        }
        if (payload.type === "error") {
          finished = true;
          onError(new Error(payload.message || "Chat failed"));
        }
      }
    }
    if (!finished) {
      onError(new Error("Chat ended unexpectedly. Please try again."));
    }
  } catch (err) {
    onError(err instanceof Error ? err : new Error("Chat stream interrupted"));
  }
}
