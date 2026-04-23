import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS } from "../lib/constants";

const lines: Array<{ text: string; color: string; size: number; weight: number }> = [
  { text: "213 cards · 61 hidden gems", color: COLORS.accentYellow, size: 48, weight: 700 },
  { text: "See the full list on Medium →", color: COLORS.fg, size: 38, weight: 600 },
  { text: "pokemon.eliseorobles.com", color: COLORS.fgDim, size: 28, weight: 500 },
];

export const CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 60px",
        gap: 22,
      }}
    >
      {lines.map((line, i) => {
        const s = spring({
          frame: frame - i * 8,
          fps,
          config: { damping: 18, stiffness: 110 },
          durationInFrames: 22,
        });
        const op = interpolate(s, [0, 1], [0, 1]);
        const ty = interpolate(s, [0, 1], [22, 0]);
        return (
          <div
            key={i}
            style={{
              fontFamily: i === 2 ? FONTS.mono : FONTS.sans,
              color: line.color,
              fontSize: line.size,
              fontWeight: line.weight,
              textAlign: "center",
              opacity: op,
              transform: `translateY(${ty}px)`,
              letterSpacing: i === 2 ? 0.5 : -0.3,
            }}
          >
            {line.text}
          </div>
        );
      })}
    </div>
  );
};
