import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

interface MarkdownContentProps {
  content: string;
}

const components: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  code: ({ className, children, ...props }) => {
    const isInline = !className;
    if (isInline) {
      return (
        <code
          style={{
            background: "rgba(37,99,235,0.08)",
            color: "#1d4ed8",
            padding: "2px 6px",
            borderRadius: 4,
            fontSize: "0.85em",
            fontFamily: '"JetBrains Mono", "Fira Code", Consolas, monospace',
          }}
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <pre
        style={{
          background: "#0f172a",
          color: "#e2e8f0",
          padding: 16,
          borderRadius: 10,
          overflow: "auto",
          fontSize: "0.85em",
          lineHeight: 1.6,
          margin: "12px 0",
          fontFamily: '"JetBrains Mono", "Fira Code", Consolas, monospace',
        }}
      >
        <code className={className} {...props}>
          {children}
        </code>
      </pre>
    );
  },
  p: ({ children }) => (
    <p style={{ margin: "0.6em 0", wordBreak: "break-word", lineHeight: 1.7 }}>{children}</p>
  ),
  li: ({ children }) => (
    <li style={{ wordBreak: "break-word", lineHeight: 1.7 }}>{children}</li>
  ),
  h1: ({ children }) => (
    <h1 style={{ fontSize: "1.3em", fontWeight: 600, margin: "0.8em 0 0.4em", lineHeight: 1.4 }}>{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 style={{ fontSize: "1.15em", fontWeight: 600, margin: "0.7em 0 0.3em", lineHeight: 1.4 }}>{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 style={{ fontSize: "1.05em", fontWeight: 600, margin: "0.6em 0 0.3em", lineHeight: 1.4 }}>{children}</h3>
  ),
  strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
  hr: () => <hr style={{ border: "none", borderTop: "1px solid #e2e8f0", margin: "1em 0" }} />,
  blockquote: ({ children }) => (
    <blockquote
      style={{
        borderLeft: "3px solid #2563eb",
        margin: "0.6em 0",
        padding: "8px 16px",
        background: "rgba(37,99,235,0.04)",
        borderRadius: "0 6px 6px 0",
      }}
    >
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div style={{ overflow: "auto", margin: "0.6em 0" }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.9em" }}>{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th
      style={{
        border: "1px solid #e2e8f0",
        padding: "8px 12px",
        background: "#f8fafc",
        fontWeight: 600,
        textAlign: "left",
      }}
    >
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td style={{ border: "1px solid #e2e8f0", padding: "8px 12px" }}>{children}</td>
  ),
  ul: ({ children }) => <ul style={{ paddingLeft: 20, margin: "0.4em 0" }}>{children}</ul>,
  ol: ({ children }) => <ol style={{ paddingLeft: 20, margin: "0.4em 0" }}>{children}</ol>,
};

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div style={{ whiteSpace: "pre-wrap" }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
