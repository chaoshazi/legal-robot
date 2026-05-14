import client from "./client";
import type { ApiResponse, ConsultationInfo } from "../types";

export const consultationApi = {
  listAll: (status?: string) =>
    client.get<ApiResponse<ConsultationInfo[]>>("/consultations", {
      params: status ? { status_filter: status } : {},
    }),

  listPending: () =>
    client.get<ApiResponse<ConsultationInfo[]>>("/consultations/pending"),

  review: (
    consultationId: string,
    body: {
      action: "publish" | "reject";
      final_answer?: string | null;
      comment?: string | null;
      score_name?: string;
      score_value?: number;
      score_comment?: string | null;
    },
  ) => client.post<ApiResponse<ConsultationInfo>>(`/consultations/${consultationId}/review`, body),
};
