import axios from "axios";
import type { ApiResponse } from "../types";

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 120000,  // 120s for PDF ingest with OCR
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        try {
          const { data } = await axios.post<ApiResponse<{ access_token: string }>>(
            "/api/v1/auth/refresh",
            { refresh_token: refreshToken },
          );
          if (data.data?.access_token) {
            localStorage.setItem("access_token", data.data.access_token);
            original.headers.Authorization = `Bearer ${data.data.access_token}`;
            return client(original);
          }
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(err);
  },
);

export default client;
