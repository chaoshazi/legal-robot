import { Card, Col, Row, Tag, Typography, Divider } from "antd";
import {
  CodeOutlined,
  BugOutlined,
  FileSearchOutlined,
  CloudUploadOutlined,
  CheckCircleOutlined,
  DesktopOutlined,
  ApiOutlined,
  DatabaseOutlined,
  SwapOutlined,
  SafetyOutlined,
  BarChartOutlined,
  BgColorsOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

const { Title, Paragraph, Text } = Typography;

interface Skill {
  command: string;
  name: string;
  description: string;
  usage: string;
  category: string;
  icon: React.ReactNode;
  color: string;
}

const skills: Skill[] = [
  {
    command: "/dev",
    name: "启动开发环境",
    description: "一键启动 Docker 基础设施（PostgreSQL + Qdrant）、后端 FastAPI（热重载）、前端 Vite 开发服务器",
    usage: "/dev",
    category: "开发",
    icon: <CodeOutlined />,
    color: "#1677ff",
  },
  {
    command: "/test",
    name: "运行测试",
    description: "运行后端 pytest 测试，支持单文件测试和覆盖率报告",
    usage: "/test\n/test tests/test_auth.py",
    category: "开发",
    icon: <BugOutlined />,
    color: "#1677ff",
  },
  {
    command: "/frontend",
    name: "前端开发辅助",
    description: "TypeScript 类型检查、Lint 检查、构建分析、查看路由和 API 调用结构",
    usage: "/frontend",
    category: "开发",
    icon: <DesktopOutlined />,
    color: "#1677ff",
  },
  {
    command: "/chat-debug",
    name: "聊天 Agent 调试",
    description: "查看 Agent 配置（tools、system prompt、knowledge_ids）、测试知识库检索、重置配置缓存、测试 LLM 连通性",
    usage: "/chat-debug",
    category: "调试",
    icon: <BugOutlined />,
    color: "#fa8c16",
  },
  {
    command: "/ingest",
    name: "知识库文档入库",
    description: "查看入库状态、上传文件并向量化入库、清空 Qdrant 集合重新入库、查看集合统计",
    usage: "/ingest",
    category: "数据",
    icon: <CloudUploadOutlined />,
    color: "#52c41a",
  },
  {
    command: "/rag",
    name: "RAG 知识库管理",
    description: "向量库配置、嵌入模型选择（mxbai-embed-large / nomic-embed-text / all-minilm）、文档分块入库流程、Agent 工具列表",
    usage: "/rag",
    category: "数据",
    icon: <DatabaseOutlined />,
    color: "#52c41a",
  },
  {
    command: "/migrate",
    name: "数据库迁移",
    description: "应用待处理迁移、自动生成迁移（alembic revision --autogenerate）、回滚、查看版本和模型列表",
    usage: "/migrate\n/migrate create\n/migrate rollback",
    category: "数据",
    icon: <SwapOutlined />,
    color: "#52c41a",
  },
  {
    command: "/seed",
    name: "初始化种子数据",
    description: "创建默认角色（user/lawyer/admin）和管理员账号，幂等设计可重复运行",
    usage: "/seed",
    category: "数据",
    icon: <BgColorsOutlined />,
    color: "#52c41a",
  },
  {
    command: "/consultation",
    name: "咨询单审核管理",
    description: "查看待审核咨询单、审核日志、咨询单完整对话历史、了解状态流转（draft → published / rejected）",
    usage: "/consultation",
    category: "业务",
    icon: <FileSearchOutlined />,
    color: "#722ed1",
  },
  {
    command: "/api",
    name: "API 设计规范",
    description: "统一响应格式（code/message/data）、错误码定义（0/1001/1002/...）、接口列表、JWT 认证方式",
    usage: "/api",
    category: "文档",
    icon: <ApiOutlined />,
    color: "#eb2f96",
  },
  {
    command: "/security",
    name: "安全规范",
    description: "JWT 双 Token、RBAC 角色权限、CORS、速率限制、审计日志 180 天保留、敏感词过滤、防 SQL 注入",
    usage: "/security",
    category: "文档",
    icon: <SafetyOutlined />,
    color: "#eb2f96",
  },
  {
    command: "/monitoring",
    name: "监控体系",
    description: "LangSmith Agent 追踪、Prometheus + Grafana 指标监控、Sentry 错误追踪、审计日志 180 天保留",
    usage: "/monitoring",
    category: "文档",
    icon: <BarChartOutlined />,
    color: "#eb2f96",
  },
  {
    command: "/qa-workflow",
    name: "全链路质量检查",
    description: "依次运行后端测试、数据库迁移检查、前端 TS 类型检查、前端 Lint、安全规范检查、审计日志保留验证，汇总报告",
    usage: "/qa-workflow",
    category: "开发",
    icon: <CheckCircleOutlined />,
    color: "#1677ff",
  },
];

const categoryColors: Record<string, string> = {
  "开发": "#1677ff",
  "调试": "#fa8c16",
  "数据": "#52c41a",
  "业务": "#722ed1",
  "文档": "#eb2f96",
};

export function SkillsPage() {
  return (
    <div style={{ padding: 32 }}>
      <div style={{ marginBottom: 32 }}>
        <Title level={3}>
          <ThunderboltOutlined style={{ marginRight: 8 }} />
          Claude Code 技能
        </Title>
        <Paragraph type="secondary" style={{ fontSize: 15, margin: 0 }}>
          本项目的 Claude Code 斜杠命令（<Text code>/command</Text>），用于快速执行开发、测试、数据管理和调试操作。
          在对话框中输入命令即可调用对应技能。
        </Paragraph>
      </div>

      {/* Category filter tags */}
      <div style={{ marginBottom: 24 }}>
        {Object.entries(categoryColors).map(([cat, color]) => (
          <Tag key={cat} color={color} style={{ fontSize: 13, padding: "2px 12px" }}>
            {cat}
          </Tag>
        ))}
      </div>

      <Divider style={{ margin: "0 0 24px" }} />

      <Row gutter={[24, 24]}>
        {skills.map((skill) => (
          <Col xs={24} sm={12} lg={8} xl={6} key={skill.command}>
            <Card
              hoverable
              style={{ height: "100%" }}
              styles={{
                body: { padding: 20, display: "flex", flexDirection: "column", height: "100%" },
              }}
            >
              <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
                <span
                  style={{
                    fontSize: 20,
                    color: skill.color,
                    marginRight: 10,
                  }}
                >
                  {skill.icon}
                </span>
                <div>
                  <Text strong style={{ fontSize: 16, fontFamily: "monospace" }}>
                    {skill.command}
                  </Text>
                  <Tag color={categoryColors[skill.category]} style={{ marginLeft: 8, fontSize: 11 }}>
                    {skill.category}
                  </Tag>
                </div>
              </div>

              <Text strong style={{ fontSize: 14, marginBottom: 8 }}>
                {skill.name}
              </Text>

              <Paragraph
                type="secondary"
                style={{ fontSize: 13, marginBottom: 12, flex: 1, lineHeight: 1.6 }}
              >
                {skill.description}
              </Paragraph>

              <div
                style={{
                  background: "#f6f8fa",
                  borderRadius: 6,
                  padding: "8px 12px",
                  fontFamily: "monospace",
                  fontSize: 12,
                  whiteSpace: "pre-wrap",
                  lineHeight: 1.8,
                  color: "#24292f",
                }}
              >
                {skill.usage}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Divider />

      <div
        style={{
          background: "#f6f8fa",
          borderRadius: 8,
          padding: "16px 24px",
          marginTop: 8,
        }}
      >
        <Title level={5} style={{ marginTop: 0 }}>
          提示
        </Title>
        <Paragraph type="secondary" style={{ margin: 0, fontSize: 13 }}>
          在 Claude Code 对话框中直接输入 <Text code>/命令名</Text> 即可调用对应技能。
          例如输入 <Text code>/dev</Text> 启动全部开发环境，输入 <Text code>/qa-workflow</Text> 执行全链路质量检查。
          技能文件位于 <Text code>~/.claude/skills/</Text> 目录，可自行修改和新增。
        </Paragraph>
      </div>
    </div>
  );
}
