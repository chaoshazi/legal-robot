import { useEffect, useState } from "react";
import { Table, Tag, Typography, Select, Space, Rate } from "antd";
import { StarOutlined } from "@ant-design/icons";
import { evaluationApi } from "../../api/evaluation";

const scoreNameLabel: Record<string, string> = {
  answer_quality: "回答质量",
};

export function EvaluationPage() {
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [scoreNames, setScoreNames] = useState<string[]>([]);
  const [filterScoreName, setFilterScoreName] = useState<string | undefined>(undefined);

  const loadScoreNames = async () => {
    try {
      const { data } = await evaluationApi.listScoreNames();
      if (data.data) setScoreNames(data.data);
    } catch {
      // ignore
    }
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const { data } = await evaluationApi.list({
        page,
        page_size: pageSize,
        score_name: filterScoreName,
      });
      if (data.data) {
        setRows(data.data.items);
        setTotal(data.data.total);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScoreNames();
  }, []);

  useEffect(() => {
    loadData();
  }, [page, pageSize, filterScoreName]);

  const columns = [
    {
      title: "评分维度",
      dataIndex: "score_name",
      key: "score_name",
      width: 120,
      render: (name: string) => (
        <Tag color="blue">{scoreNameLabel[name] || name}</Tag>
      ),
    },
    {
      title: "评分",
      dataIndex: "score_value",
      key: "score_value",
      width: 160,
      render: (val: number) => (
        <Rate disabled value={val / 2} count={5} character={<StarOutlined />} />
      ),
    },
    {
      title: "数值",
      dataIndex: "score_value",
      key: "score_value_num",
      width: 60,
      render: (val: number) => <Typography.Text strong>{val}/10</Typography.Text>,
    },
    {
      title: "用户问题",
      dataIndex: "question",
      key: "question",
      ellipsis: true,
      render: (text: string) => (
        <Typography.Paragraph
          ellipsis={{ rows: 2 }}
          style={{ margin: 0, maxWidth: 360 }}
          copyable={{ text }}
        >
          {text || "-"}
        </Typography.Paragraph>
      ),
    },
    {
      title: "评语",
      dataIndex: "comment",
      key: "comment",
      ellipsis: true,
      render: (text: string | null) =>
        text || <Typography.Text type="secondary">-</Typography.Text>,
    },
    {
      title: "评估时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (t: string) => t?.slice(0, 19).replace("T", " "),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>
        <StarOutlined /> 评估管理
      </Typography.Title>

      <Space style={{ marginBottom: 16 }}>
        <Select
          allowClear
          placeholder="评分维度"
          style={{ width: 160 }}
          value={filterScoreName}
          onChange={(v) => {
            setFilterScoreName(v);
            setPage(1);
          }}
          options={scoreNames.map((n) => ({
            label: scoreNameLabel[n] || n,
            value: n,
          }))}
        />
      </Space>

      <Table
        dataSource={rows}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: false,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
        locale={{ emptyText: "暂无评估记录" }}
      />
    </div>
  );
}
