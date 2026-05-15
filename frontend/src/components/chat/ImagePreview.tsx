import { Image } from "antd";

interface ImagePreviewProps {
  src: string;
  filename: string;
}

export function ImagePreview({ src, filename }: ImagePreviewProps) {
  return (
    <div style={{ marginBottom: 8 }}>
      <Image
        src={src}
        alt={filename}
        style={{
          maxWidth: "100%",
          maxHeight: 300,
          borderRadius: 8,
          objectFit: "contain",
          background: "#f1f5f9",
        }}
        preview={{
          mask: "点击预览",
        }}
      />
    </div>
  );
}
