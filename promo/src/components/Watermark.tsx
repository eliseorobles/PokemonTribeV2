import React from "react";
import { useVideoConfig } from "remotion";
import { COLORS, FONTS, Orientation, safeTopFor, SAFE_H, SAFE_W } from "../lib/constants";

/**
 * Persistent "eliseorobles.com" mark. Sits in the bottom-right of the safe
 * area so it's visible in BOTH the vertical (1080x1920) and square (1080x1080)
 * renders. Low opacity — visible enough to deter reuploads, subtle enough to
 * not compete with the scene content.
 */
type Props = {
  orientation: Orientation;
};

export const Watermark: React.FC<Props> = ({ orientation }) => {
  const { width, height } = useVideoConfig();
  // Anchor to the bottom-right of the SAFE box (which is 1080x1080 centered
  // inside the full canvas). Keeps mark positioned identically on both crops.
  const safeTop = safeTopFor(orientation);
  return (
    <div
      style={{
        position: "absolute",
        top: safeTop + SAFE_H - 56,
        left: (width - SAFE_W) / 2 + SAFE_W - 300,
        width: 272,
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        gap: 10,
        opacity: 0.55,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          width: 18,
          height: 18,
          borderRadius: 9,
          background:
            `linear-gradient(135deg, ${COLORS.accentYellow}, ${COLORS.accentBlue})`,
          boxShadow: "0 0 8px rgba(255,203,5,0.35)",
        }}
      />
      <div
        style={{
          fontFamily: FONTS.mono,
          fontSize: 18,
          color: COLORS.fg,
          fontWeight: 600,
          letterSpacing: 0.4,
        }}
      >
        eliseorobles.com
      </div>
    </div>
  );
};
