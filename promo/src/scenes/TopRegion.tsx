import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS } from "../lib/constants";
import { Counter } from "../components/Counter";
import { useStats } from "../lib/stats";

export const TopRegion: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const stats = useStats();

  const titleOpacity = interpolate(frame, [0, 14], [0, 1], {
    extrapolateRight: "clamp",
  });

  const numberEnter = spring({
    frame: frame - 12,
    fps,
    config: { damping: 16, stiffness: 90 },
    durationInFrames: 30,
  });
  const numberScale = interpolate(numberEnter, [0, 1], [0.7, 1]);

  const barsEnter = spring({
    frame: frame - 55,
    fps,
    config: { damping: 22, stiffness: 100 },
    durationInFrames: 26,
  });
  const barsOpacity = interpolate(barsEnter, [0, 1], [0, 1]);
  const barsY = interpolate(barsEnter, [0, 1], [80, 0]);

  const topR = stats?.top_roi_r ?? 0.44;
  const topName = (stats?.top_roi ?? "occipital_L").replace("_", " ");

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
          fontFamily: FONTS.sans,
          color: COLORS.fgDim,
          fontSize: 28,
          letterSpacing: 3,
          textTransform: "uppercase",
          opacity: titleOpacity,
        }}
      >
        Strongest single region
      </div>

      <div
        style={{
          fontFamily: FONTS.serif,
          color: COLORS.fg,
          fontSize: 64,
          fontWeight: 600,
          letterSpacing: -1.5,
          opacity: titleOpacity,
        }}
      >
        Left visual cortex
      </div>

      <div
        style={{
          fontFamily: FONTS.mono,
          color: COLORS.good,
          fontSize: 180,
          fontWeight: 800,
          letterSpacing: -4,
          transform: `scale(${numberScale})`,
          opacity: interpolate(frame, [10, 25], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        r ={" "}
        <Counter
          from={0}
          to={topR}
          startFrame={16}
          durationFrames={28}
          decimals={2}
          signed
        />
      </div>

      <div
        style={{
          marginTop: 18,
          background: "#fff",
          padding: 10,
          borderRadius: 12,
          maxWidth: 880,
          opacity: barsOpacity,
          transform: `translateY(${barsY}px)`,
        }}
      >
        <Img
          src={staticFile("stats/correlation-bars.png")}
          style={{ width: "100%", display: "block", borderRadius: 6 }}
        />
      </div>
    </div>
  );
};
