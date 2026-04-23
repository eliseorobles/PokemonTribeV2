import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS } from "../lib/constants";

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const eyebrowOpacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });
  const titleEnter = spring({
    frame: frame - 8,
    fps,
    config: { damping: 18, stiffness: 90 },
    durationInFrames: 30,
  });
  const titleOpacity = interpolate(titleEnter, [0, 1], [0, 1]);
  const titleY = interpolate(titleEnter, [0, 1], [28, 0]);

  const subOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "0 80px",
        gap: 24,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontFamily: FONTS.mono,
          color: COLORS.accentYellow,
          fontSize: 28,
          letterSpacing: 4.5,
          textTransform: "uppercase",
          opacity: eyebrowOpacity,
          fontWeight: 700,
        }}
      >
        A Thought Experiment
      </div>
      <div
        style={{
          fontFamily: FONTS.serif,
          color: COLORS.fg,
          fontSize: 92,
          lineHeight: 1.02,
          fontWeight: 600,
          letterSpacing: -1.5,
          maxWidth: 960,
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        Can a brain see which&nbsp;Pokémon cards are valuable?
      </div>
      <div
        style={{
          fontFamily: FONTS.sans,
          color: COLORS.fgDim,
          fontSize: 28,
          opacity: subOpacity,
          marginTop: 12,
        }}
      >
        I fed 213 cards into Meta's fMRI model.
      </div>
    </div>
  );
};
