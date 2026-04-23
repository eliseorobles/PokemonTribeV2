export const FPS = 30;

// Scene durations (frames at 30fps)
export const INTRO_DURATION = 60;       // 2.0s
export const CARD_REEL_DURATION = 150;  // 5.0s
export const STAT_REVEAL_DURATION = 150; // 5.0s
export const TOP_REGION_DURATION = 120; // 4.0s
export const CTA_DURATION = 60;         // 2.0s

export const TOTAL_DURATION =
  INTRO_DURATION +
  CARD_REEL_DURATION +
  STAT_REVEAL_DURATION +
  TOP_REGION_DURATION +
  CTA_DURATION;

// Colors — matches site + posts palette
export const COLORS = {
  bg: "#0e0e15",
  bgElev: "#161624",
  bgSoft: "#1f1f31",
  fg: "#f4f4f0",
  fgDim: "#9ba0b3",
  fgMuted: "#6b7280",
  accentYellow: "#ffcb05",
  accentBlue: "#3d7dca",
  good: "#4ade80",
  bad: "#f87171",
  line: "#2a2a3f",
};

export const FONTS = {
  serif: "Georgia, 'Times New Roman', serif",
  sans:
    "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif",
  mono: "'SF Mono', 'JetBrains Mono', Menlo, monospace",
};

// Safe area — center 1080x1080 box, used inside vertical 1080x1920 too
export const SAFE_W = 1080;
export const SAFE_H = 1080;

export type Orientation = "vertical" | "square";

export const dimsFor = (orientation: Orientation) =>
  orientation === "vertical"
    ? { width: 1080, height: 1920 }
    : { width: 1080, height: 1080 };

// Vertical offset of the safe box inside the full canvas
export const safeTopFor = (orientation: Orientation) =>
  orientation === "vertical" ? (1920 - SAFE_H) / 2 : 0;
