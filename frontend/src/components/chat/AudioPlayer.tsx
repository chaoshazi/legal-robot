import { useEffect, useRef, useState } from "react";
import { PlayCircleOutlined, PauseCircleOutlined } from "@ant-design/icons";

interface AudioPlayerProps {
  src: string;
}

export function AudioPlayer({ src }: AudioPlayerProps) {
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onLoaded = () => setDuration(audio.duration);
    const onTime = () => setCurrentTime(audio.currentTime);
    const onEnd = () => {
      setPlaying(false);
      setCurrentTime(0);
    };

    audio.addEventListener("loadedmetadata", onLoaded);
    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("ended", onEnd);
    return () => {
      audio.removeEventListener("loadedmetadata", onLoaded);
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("ended", onEnd);
    };
  }, []);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (playing) {
      audio.pause();
    } else {
      audio.play().catch(() => {});
    }
    setPlaying(!playing);
  };

  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 14px",
        background: "rgba(0,0,0,0.04)",
        borderRadius: 20,
        marginBottom: 8,
        minWidth: 200,
      }}
    >
      <audio ref={audioRef} src={src} preload="metadata" />
      <div
        onClick={toggle}
        style={{ cursor: "pointer", fontSize: 20, lineHeight: 1, display: "flex", alignItems: "center" }}
      >
        {playing ? <PauseCircleOutlined style={{ color: "#2563eb" }} /> : <PlayCircleOutlined style={{ color: "#2563eb" }} />}
      </div>
      <div
        style={{
          flex: 1,
          height: 4,
          background: "rgba(0,0,0,0.1)",
          borderRadius: 2,
          position: "relative",
        }}
      >
        <div
          style={{
            width: `${progress}%`,
            height: "100%",
            background: "#2563eb",
            borderRadius: 2,
            transition: "width 0.2s",
          }}
        />
      </div>
      <span style={{ fontSize: 12, color: "#64748b", minWidth: 40, textAlign: "right" }}>
        {playing ? fmt(currentTime) : fmt(duration || 0)}
      </span>
    </div>
  );
}
