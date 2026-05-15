import { useState, useRef, useEffect, useCallback } from "react";
import { Button, message, Spin, Tooltip } from "antd";
import {
  AudioOutlined,
  StopOutlined,
  CheckCircleOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import { uploadApi } from "../../api/upload";

type RecorderStatus =
  | { type: "idle" }
  | { type: "recording"; elapsed: number }
  | { type: "uploading" }
  | { type: "transcribing" }
  | { type: "done"; text: string; attachmentId: string }
  | { type: "error"; message: string };

interface VoiceRecorderProps {
  sessionId: string | null;
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

const MAX_RECORDING_SECONDS = 120;

export function VoiceRecorder({ sessionId, onTranscription, disabled }: VoiceRecorderProps) {
  const [status, setStatus] = useState<RecorderStatus>({ type: "idle" });
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // Check browser support
  const supported = typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined";

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      startTimeRef.current = Date.now();

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach((t) => t.stop());

        const blob = new Blob(chunksRef.current, { type: mimeType });
        if (blob.size === 0) {
          setStatus({ type: "error", message: "录音为空" });
          return;
        }

        // Upload
        setStatus({ type: "uploading" });
        try {
          const file = new File([blob], `voice_${Date.now()}.webm`, { type: mimeType });
          const { data: uploadRes } = await uploadApi.upload(file, sessionId || undefined);

          if (!uploadRes.data) {
            setStatus({ type: "error", message: "上传失败" });
            return;
          }

          // Transcribe
          setStatus({ type: "transcribing" });
          const { data: transcribeRes } = await uploadApi.transcribe(uploadRes.data.id);

          if (transcribeRes.data?.transcription) {
            const text = transcribeRes.data.transcription;
            setStatus({ type: "done", text, attachmentId: uploadRes.data.id });
            onTranscription(text);
          } else {
            setStatus({ type: "error", message: "转写失败" });
          }
        } catch {
          setStatus({ type: "error", message: "处理失败，请重试" });
        }
      };

      recorder.onerror = () => {
        setStatus({ type: "error", message: "录音出错" });
        cleanup();
      };

      recorder.start(250); // collect data every 250ms
      setStatus({ type: "recording", elapsed: 0 });

      // Timer for elapsed time and max duration
      timerRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        if (elapsed >= MAX_RECORDING_SECONDS) {
          stopRecording();
        } else {
          setStatus((prev) =>
            prev.type === "recording" ? { ...prev, elapsed } : prev
          );
        }
      }, 1000);
    } catch {
      setStatus({ type: "error", message: "无法访问麦克风" });
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const reset = () => {
    cleanup();
    setStatus({ type: "idle" });
  };

  if (!supported) return null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      {status.type === "idle" && (
        <Tooltip title="语音输入">
          <Button
            type="default"
            icon={<AudioOutlined style={{ fontSize: 16 }} />}
            onClick={startRecording}
            disabled={disabled}
            style={{ display: "inline-flex", alignItems: "center", justifyContent: "center" }}
          />
        </Tooltip>
      )}

      {status.type === "recording" && (
        <>
          <Button
            type="text"
            danger
            icon={<StopOutlined style={{ fontSize: 16 }} />}
            onClick={stopRecording}
          />
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 12,
              color: "#ef4444",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                background: "#ef4444",
                animation: "pulse 1s ease-in-out infinite",
              }}
            />
            {status.elapsed}s
          </div>
        </>
      )}

      {status.type === "uploading" && (
        <div style={{ padding: "4px 8px" }}>
          <Spin size="small" />
          <span style={{ fontSize: 12, color: "var(--text-secondary)", marginLeft: 6 }}>上传中...</span>
        </div>
      )}

      {status.type === "transcribing" && (
        <div style={{ padding: "4px 8px" }}>
          <Spin size="small" />
          <span style={{ fontSize: 12, color: "var(--text-secondary)", marginLeft: 6 }}>转写中...</span>
        </div>
      )}

      {status.type === "done" && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            fontSize: 12,
            color: "#16a34a",
            padding: "4px 8px",
          }}
        >
          <CheckCircleOutlined />
          转写完成
          <Button type="text" size="small" icon={<CloseOutlined />} onClick={reset} />
        </div>
      )}

      {status.type === "error" && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            fontSize: 12,
            color: "#ef4444",
            padding: "4px 8px",
          }}
        >
          {status.message}
          <Button type="text" size="small" icon={<CloseOutlined />} onClick={reset} />
        </div>
      )}
    </div>
  );
}
