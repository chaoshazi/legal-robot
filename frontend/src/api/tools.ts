import client from "./client";
import type { ApiResponse, Tool } from "../types";

export async function listTools(): Promise<ApiResponse<Tool[]>> {
  const { data } = await client.get("/tools");
  return data;
}

export async function createTool(body: {
  name: string;
  description?: string;
  function_name: string;
  parameters?: string;
  tool_type?: string;
}): Promise<ApiResponse<Tool>> {
  const { data } = await client.post("/tools", body);
  return data;
}

export async function updateTool(
  id: string,
  body: Partial<{
    name: string;
    description: string;
    function_name: string;
    parameters: string;
    tool_type: string;
    enabled: boolean;
  }>,
): Promise<ApiResponse<Tool>> {
  const { data } = await client.put(`/tools/${id}`, body);
  return data;
}

export async function deleteTool(id: string): Promise<ApiResponse<null>> {
  const { data } = await client.delete(`/tools/${id}`);
  return data;
}
