import client from "./client";
import type { ApiResponse } from "../types";

export interface EvaluationListData {
  items: {
    id: number;
    consultation_id: string;
    trace_id: string;
    score_name: string;
    score_value: number;
    data_type: string;
    comment: string | null;
    evaluated_by: string | null;
    question: string;
    created_at: string;
  }[];
  total: number;
  page: number;
  page_size: number;
}

export const evaluationApi = {
  list: (params: {
    page?: number;
    page_size?: number;
    score_name?: string;
    consultation_id?: string;
    evaluated_by?: string;
  }) =>
    client.get<ApiResponse<EvaluationListData>>("/evaluations", { params }),

  listScoreNames: () =>
    client.get<ApiResponse<string[]>>("/evaluations/score-names"),
};
