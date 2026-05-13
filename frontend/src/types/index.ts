// API response types
export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T | null;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface QaRecord {
  id: string;
  question: string;
  answer: string;
  sources: LawReference[] | null;
  created_at: string;
}

export interface LawReference {
  law: string;
  article: string;
  text: string;
}

export interface MCPServer {
  id: string;
  name: string;
  transport: string;
  command: string | null;
  args: string | null;
  url: string | null;
  description: string | null;
  status: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMConfig {
  provider: "ollama" | "deepseek" | "llamacpp";
  ollama_base_url: string;
  ollama_model: string;
  ollama_embed_model: string;
  deepseek_api_key: string;
  deepseek_api_base: string;
  deepseek_model: string;
  llamacpp_base_url: string;
  llamacpp_model: string;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  function_name: string;
  parameters: string | null;
  tool_type: "builtin" | "custom";
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AgentConfig {
  system_prompt: string;
  active_tool_ids: string[];
  active_mcp_ids: string[];
  active_knowledge_ids: string[];
}

export interface UnifiedConfig {
  provider: string;
  ollama_base_url: string;
  ollama_model: string;
  ollama_embed_model: string;
  deepseek_api_key: string;
  deepseek_api_base: string;
  deepseek_model: string;
  llamacpp_base_url: string;
  llamacpp_model: string;
  system_prompt: string;
  active_tool_ids: string[];
  active_mcp_ids: string[];
  active_knowledge_ids: string[];
}

export interface MenuItem {
  key: string;
  label: string;
}

export interface RolePermission {
  role_id: number;
  role_name: string;
  menu_keys: string[];
}

export interface PermissionMatrix {
  roles: RolePermission[];
  menus: MenuItem[];
}

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_size: number;
  chunk_count: number | null;
  status: string;
  error: string | null;
  created_at: string;
}

export interface OllamaModelInfo {
  name: string;
  model: string;
  parameter_size: string;
  quantization_level: string;
  size: number;
  modified_at: string;
}

export interface ConsultationInfo {
  id: string;
  user_id: string;
  session_id: string;
  question: string;
  draft_answer: string | null;
  final_answer: string | null;
  status: string;
  reviewer_id: string | null;
  review_comment: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface UserAdmin {
  id: string;
  email: string;
  display_name: string;
  phone: string | null;
  role_id: number;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Role {
  id: number;
  name: string;
  description: string | null;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  display_name: string;
  role_id: number;
}

export interface CreateRoleRequest {
  name: string;
  description?: string;
}
