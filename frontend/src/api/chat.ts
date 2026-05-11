import client from "./client";
import type { ApiResponse } from "../types";

export const chatApi = {
  createSession: (data: { title: string }) =>
    client.post<ApiResponse<{ id: string; title: string }>>("/chat/sessions", data),

  listSessions: () =>
    client.get<ApiResponse<{ id: string; title: string; status: string; created_at: string }[]>>("/chat/sessions"),

  getMessages: (sessionId: string) =>
    client.get<ApiResponse<{ role: string; content: string; created_at: string }[]>>(`/chat/sessions/${sessionId}/messages`),

  renameSession: (sessionId: string, title: string) =>
    client.put<ApiResponse<{ id: string; title: string }>>(`/chat/sessions/${sessionId}`, { title }),

  deleteSession: (sessionId: string) =>
    client.delete<ApiResponse<null>>(`/chat/sessions/${sessionId}`),

  send: (data: { session_id: string; content: string }) =>
    client.post<ApiResponse<{ answer: string }>>("/chat/ask", data),
};
