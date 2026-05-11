import client from "./client";
import type { ApiResponse, AgentConfig } from "../types";

export async function getAgentConfig(): Promise<ApiResponse<AgentConfig>> {
  const { data } = await client.get("/settings/agent");
  return data;
}

export async function updateAgentConfig(
  body: AgentConfig,
): Promise<ApiResponse<AgentConfig>> {
  const { data } = await client.put("/settings/agent", body);
  return data;
}
