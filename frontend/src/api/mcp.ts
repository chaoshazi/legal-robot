import client from "./client";
import type { ApiResponse, MCPServer } from "../types";

export async function listServers(): Promise<ApiResponse<MCPServer[]>> {
  const { data } = await client.get("/mcp/servers");
  return data;
}

export async function createServer(body: {
  name: string;
  transport: string;
  command?: string;
  args?: string;
  url?: string;
  api_key?: string;
  description?: string;
}): Promise<ApiResponse<MCPServer>> {
  const { data } = await client.post("/mcp/servers", body);
  return data;
}

export async function updateServer(
  id: string,
  body: Partial<{
    name: string;
    transport: string;
    command: string;
    args: string;
    url: string;
    api_key: string;
    description: string;
    enabled: boolean;
  }>
): Promise<ApiResponse<MCPServer>> {
  const { data } = await client.put(`/mcp/servers/${id}`, body);
  return data;
}

export async function deleteServer(id: string): Promise<ApiResponse<null>> {
  const { data } = await client.delete(`/mcp/servers/${id}`);
  return data;
}

export async function testConnection(id: string): Promise<ApiResponse<{ status: string; message: string }>> {
  const { data } = await client.post(`/mcp/servers/${id}/test`);
  return data;
}

export async function listServerTools(id: string): Promise<ApiResponse<{ server_id: string; tools_count: number; tools: string[] }>> {
  const { data } = await client.get(`/mcp/servers/${id}/tools`);
  return data;
}

export async function toggleServer(id: string): Promise<ApiResponse<{ id: string; enabled: boolean }>> {
  const { data } = await client.post(`/mcp/servers/${id}/toggle`);
  return data;
}
