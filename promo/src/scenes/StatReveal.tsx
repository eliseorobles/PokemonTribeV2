import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS } from "../lib/constants";
import { HistogramBars } from "../components/HistogramBars";
import { Counter } from "../components/Counter";
import { useStats } from "../lib/stats";

export const StatReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const stats = useStats();

  const titleEnter = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 90 },
    durationInFrames: 24,
  });
  const titleOpacity = interpolate(titleEnter, [0, 1], [0, 1]);
  const titleY = interpolate(titleEnter, [0, 1], [18, 0]);

  const subOpacity = interpolate(frame, [80, 110], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const realR2 = stats?.r2_real ?? 0.095;
  const pct = stats?.percentile_in_null ?? 100;

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
        gap: 28,
      }}
    >
      <div
        style={{
          fontFamily: FONTS.serif,
          color: COLORS.fg,
          fontSize: 62,
          lineHeight: 1.1,
          fontWeight: 600,
          maxWidth: 900,
          textAlign: "center",
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          letterSpacing: -1,
        }}
      >
        Real model vs. 200 shuffled controls
      </div>

      <div
        style={{
          marginTop: 12,
          padding: "28px 40px",
          background: COLORS.bgElev,
          border: `1px solid ${COLORS.line}`,
          borderRadius: 16,
        }}
      >
        <HistogramBars
          startFrame={12}
          growFrames={60}
          realR2={realR2}
          width={860}
          height={280}
        />
      </div>

      <div
        style={{
          fontFamily: FONTS.sans,
          color: COLORS.fg,
          fontSize: 38,
          fontWeight: 600,
          textAlign: "center",
          opacity: subOpacity,
        }}
      >
        Real model beats&nbsp;
        <span
          style={{
            color: COLORS.accentYellow,
            fontFamily: FONTS.mono,
            fontWeight: 700,
          }}
        >
          <Counter
            from={0}
            to={pct}
            startFrame={80}
            durationFrames={30}
            decimals={0}
            suffix="%"
          />
        </span>
        &nbsp;of shuffles
      </div>
    </div>
  );
};
