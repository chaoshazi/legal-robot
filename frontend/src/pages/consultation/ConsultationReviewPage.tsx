import { useEffect, useState } from "react";
import {
  Table, Button, Tag, Space, message, Modal, Input, Typography, Tabs, Descriptions, Divider, Rate,
} from "antd";
import {
  CheckCircleOutlined, CloseCircleOutlined, EyeOutlined, FileTextOutlined, StarOutlined,
} from "@ant-design/icons";
import { consultationApi } from "../../api/consultation";
import { useAuthStore } from "../../stores/authStore";
import type { ConsultationInfo } from "../../types";

const statusColor: Record<string, string> = {
  draft: "orange",
  published: "success",
  rejected: "error",
};

const statusLabel: Record<string, string> = {
  draft: "待审核",
  published: "已发布",
  rejected: "已驳回",
};

export function ConsultationReviewPage() {
  const user = useAuthStore((s) => s.user);
  const isLawyerOrAdmin = user?.role === "lawyer" || user?.role === "admin";

  const [consultations, setConsultations] = useState<ConsultationInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<string>(isLawyerOrAdmin ? "pending" : "all");

  // Review modal
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewing, setReviewing] = useState<ConsultationInfo | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [comment, setComment] = useState("");
  const [scoreValue, setScoreValue] = useState(0);
  const [scoreComment, setScoreComment] = useState("");

  const loadAll = async () => {
    setLoading(true);
    try {
      const { data } = await consultationApi.listAll(activeTab === "all" ? undefined : activeTab);
      if (data.data) setConsultations(data.data);
    } catch {
      message.error("加载咨询单失败");
    } finally {
      setLoading(false);
    }
  };

  const loadPending = async () => {
    setLoading(true);
    try {
      const { data } = await consultationApi.listPending();
      if (data.data) setConsultations(data.data);
    } catch {
      message.error("加载待审列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "pending") {
      loadPending();
    } else {
      loadAll();
    }
  }, [activeTab]);

  const openReview = (c: ConsultationInfo) => {
    setReviewing(c);
    setFinalAnswer(c.draft_answer ?? "");
    setComment("");
    setScoreValue(0);
    setScoreComment("");
    setReviewOpen(true);
  };

  const handleReview = async (action: "publish" | "reject") => {
    if (!reviewing) return;
    setSubmitting(true);
    try {
      await consultationApi.review(reviewing.id, {
        action,
        final_answer: action === "publish" ? finalAnswer : null,
        comment: comment || null,
        score_name: action === "publish" && scoreValue > 0 ? "answer_quality" : undefined,
        score_value: action === "publish" && scoreValue > 0 ? scoreValue : undefined,
        score_comment: action === "publish" && scoreValue > 0 ? (scoreComment || null) : undefined,
      });
      message.success(action === "publish" ? "已发布" : "已驳回");
      setReviewOpen(false);
      setReviewing(null);
      // Reload list
      if (activeTab === "pending") loadPending();
      else loadAll();
    } catch {
      message.error("操作失败");
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      title: "问题",
      dataIndex: "question",
      key: "question",
      ellipsis: true,
      render: (text: string) => (
        <Typography.Paragraph
          ellipsis={{ rows: 2 }}
          style={{ margin: 0, maxWidth: 360 }}
          copyable={{ text }}
        >
          {text}
        </Typography.Paragraph>
      ),
    },
    {
      title: "AI 回答",
      dataIndex: "draft_answer",
      key: "draft_answer",
      ellipsis: true,
      render: (text: string | null) =>
        text ? (
          <Typography.Paragraph ellipsis={{ rows: 2 }} style={{ margin: 0, maxWidth: 360 }}>
            {text.slice(0, 200)}
          </Typography.Paragraph>
        ) : (
          <Typography.Text type="secondary">-</Typography.Text>
        ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (s: string) => <Tag color={statusColor[s] || "default"}>{statusLabel[s] || s}</Tag>,
    },
    {
      title: "提交时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (t: string) => t?.slice(0, 19).replace("T", " "),
    },
    {
      title: "操作",
      key: "action",
      width: 120,
      render: (_: unknown, record: ConsultationInfo) => (
        <Space>
          {(isLawyerOrAdmin && record.status === "draft") ? (
            <Button type="primary" size="small" icon={<EyeOutlined />} onClick={() => openReview(record)}>
              审核
            </Button>
          ) : (
            <Button size="small" icon={<EyeOutlined />} onClick={() => openReview(record)}>
              查看
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const tabItems = isLawyerOrAdmin
    ? [
        { key: "pending", label: "待审核", children: null },
        { key: "draft", label: "草稿", children: null },
        { key: "published", label: "已发布", children: null },
        { key: "rejected", label: "已驳回", children: null },
        { key: "all", label: "全部", children: null },
      ]
    : [
        { key: "all", label: "全部", children: null },
        { key: "draft", label: "草稿", children: null },
        { key: "published", label: "已发布", children: null },
      ];

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>
        <FileTextOutlined /> 咨询单管理
      </Typography.Title>

      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />

      <Table
        dataSource={consultations}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 15, showSizeChanger: false }}
        locale={{ emptyText: "暂无咨询单" }}
      />

      {/* Review Modal */}
      <Modal
        title="审核咨询单"
        open={reviewOpen}
        onCancel={() => setReviewOpen(false)}
        width={800}
        footer={
          reviewing?.status === "draft" && isLawyerOrAdmin
            ? [
                <Button key="cancel" onClick={() => setReviewOpen(false)}>
                  关闭
                </Button>,
                <Button
                  key="reject"
                  danger
                  icon={<CloseCircleOutlined />}
                  loading={submitting}
                  onClick={() => handleReview("reject")}
                >
                  驳回
                </Button>,
                <Button
                  key="publish"
                  type="primary"
                  icon={<CheckCircleOutlined />}
                  loading={submitting}
                  onClick={() => handleReview("publish")}
                >
                  发布
                </Button>,
              ]
            : [
                <Button key="cancel" onClick={() => setReviewOpen(false)}>
                  关闭
                </Button>,
              ]
        }
      >
        {reviewing && (
          <div style={{ marginTop: 8 }}>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="状态">
                <Tag color={statusColor[reviewing.status] || "default"}>
                  {statusLabel[reviewing.status] || reviewing.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="提交时间">
                {reviewing.created_at?.slice(0, 19).replace("T", " ")}
              </Descriptions.Item>
              {reviewing.reviewed_at && (
                <Descriptions.Item label="审核时间">
                  {reviewing.reviewed_at.slice(0, 19).replace("T", " ")}
                </Descriptions.Item>
              )}
            </Descriptions>

            <Divider orientation="left" plain>用户问题</Divider>
            <div style={{
              padding: "12px 16px",
              background: "#f6f8fa",
              borderRadius: 6,
              whiteSpace: "pre-wrap",
            }}>
              {reviewing.question}
            </div>

            <Divider orientation="left" plain>
              {reviewing.status === "draft" ? "AI 草稿答案（可编辑）" : "AI 草稿答案"}
            </Divider>
            {reviewing.status === "draft" && isLawyerOrAdmin ? (
              <Input.TextArea
                rows={8}
                value={finalAnswer}
                onChange={(e) => setFinalAnswer(e.target.value)}
                style={{ whiteSpace: "pre-wrap" }}
              />
            ) : (
              <div style={{
                padding: "12px 16px",
                background: "#f6f8fa",
                borderRadius: 6,
                whiteSpace: "pre-wrap",
              }}>
                {reviewing.draft_answer || "(无)"}
              </div>
            )}

            {reviewing.final_answer && (
              <>
                <Divider orientation="left" plain>最终发布内容</Divider>
                <div style={{
                  padding: "12px 16px",
                  background: "#f0fff0",
                  borderRadius: 6,
                  whiteSpace: "pre-wrap",
                  border: "1px solid #b7eb8f",
                }}>
                  {reviewing.final_answer}
                </div>
              </>
            )}

            {reviewing.status === "draft" && isLawyerOrAdmin && (
              <>
                <Divider orientation="left" plain>评分（发布时提交）</Divider>
                <Space direction="vertical" style={{ width: "100%" }}>
                  <Space>
                    <Typography.Text strong>回答质量：</Typography.Text>
                    <Rate
                      value={scoreValue / 2}
                      count={5}
                      onChange={(v) => setScoreValue(v * 2)}
                      character={<StarOutlined />}
                    />
                    <Typography.Text type="secondary">
                      {scoreValue > 0 ? `${scoreValue}/10` : "未评分"}
                    </Typography.Text>
                  </Space>
                  <Input.TextArea
                    rows={2}
                    value={scoreComment}
                    onChange={(e) => setScoreComment(e.target.value)}
                    placeholder="评分备注（可选）..."
                  />
                </Space>

                <Divider orientation="left" plain>审核意见（可选）</Divider>
                <Input.TextArea
                  rows={3}
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="输入审核意见..."
                />
              </>
            )}

            {reviewing.review_comment && (
              <>
                <Divider orientation="left" plain>审核意见</Divider>
                <div style={{ padding: "8px 12px", background: "#fffbe6", borderRadius: 6 }}>
                  {reviewing.review_comment}
                </div>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
