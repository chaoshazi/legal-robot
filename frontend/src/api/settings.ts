import client from "./client";
import type { ApiResponse, LLMConfig, OllamaModelInfo, UnifiedConfig } from "../types";

export async function getLLMConfig(): Promise<ApiResponse<LLMConfig>> {
  const { data } = await client.get("/settings/llm");
  return data;
}

export async function updateLLMConfig(body: LLMConfig): Promise<ApiResponse<LLMConfig>> {
  const { data } = await client.put("/settings/llm", body);
  return data;
}

export async function getUnifiedConfig(): Promise<ApiResponse<UnifiedConfig>> {
  const { data } = await client.get("/settings/unified");
  return data;
}

export async function updateUnifiedConfig(
  body: UnifiedConfig,
): Promise<ApiResponse<UnifiedConfig>> {
  const { data } = await client.put("/settings/unified", body);
  return data;
}

export async function getOllamaModels(): Promise<ApiResponse<OllamaModelInfo[]>> {
  const { data } = await client.get("/settings/ollama-models");
  return data;
}

export async function getOllamaEmbedModels(): Promise<ApiResponse<OllamaModelInfo[]>> {
  const { data } = await client.get("/settings/ollama-embed-models");
  return data;
}
