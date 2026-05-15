import {
  FileTextOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  FileOutlined,
} from "@ant-design/icons";

interface FileAttachmentProps {
  filename: string;
  fileSize: number;
  fileType: string;
  downloadUrl: string;
}

function getFileIcon(mimeType: string) {
  if (mimeType.includes("pdf")) return <FilePdfOutlined style={{ color: "#ef4444", fontSize: 24 }} />;
  if (mimeType.includes("wordprocessingml") || mimeType.includes("doc")) return <FileWordOutlined style={{ color: "#2563eb", fontSize: 24 }} />;
  if (mimeType.includes("spreadsheet") || mimeType.includes("xls")) return <FileExcelOutlined style={{ color: "#16a34a", fontSize: 24 }} />;
  if (mimeType.includes("text")) return <FileTextOutlined style={{ color: "#64748b", fontSize: 24 }} />;
  return <FileOutlined style={{ color: "#64748b", fontSize: 24 }} />;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileAttachment({ filename, fileSize, fileType, downloadUrl }: FileAttachmentProps) {
  return (
    <a
      href={downloadUrl}
      target="_blank"
      rel="noopener noreferrer"
      style={{ textDecoration: "none" }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "10px 14px",
          background: "rgba(0,0,0,0.03)",
          borderRadius: 10,
          marginBottom: 8,
          border: "1px solid rgba(0,0,0,0.06)",
          transition: "background 0.2s",
          cursor: "pointer",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(0,0,0,0.06)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(0,0,0,0.03)")}
      >
        {getFileIcon(fileType)}
        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: "#1e293b",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {filename}
          </div>
          <div style={{ fontSize: 11, color: "#94a3b8" }}>{formatSize(fileSize)}</div>
        </div>
      </div>
    </a>
  );
}
