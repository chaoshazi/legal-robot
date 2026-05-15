import client from "./client";
import type { ApiResponse } from "../types";

export interface UploadResult {
  id: string;
  filename: string;
  file_size: number;
  file_type: string;
  mime_type: string;
  status: string;
  url?: string;
}

export const uploadApi = {
  upload: (file: File, sessionId?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (sessionId) formData.append("session_id", sessionId);
    return client.post<ApiResponse<UploadResult>>("/chat/upload", formData, {
      headers: { "Content-Type": null },
      timeout: 120000,
    });
  },

  transcribe: (attachmentId: string) =>
    client.post<ApiResponse<{ transcription: string; attachment_id: string }>>(`/chat/transcribe/${attachmentId}`),

  getDownloadUrl: (attachmentId: string) => `/api/v1/chat/download/${attachmentId}`,
};
