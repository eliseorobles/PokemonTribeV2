import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

type Props = {
  from: number;
  to: number;
  startFrame?: number;
  durationFrames?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  signed?: boolean;
  style?: React.CSSProperties;
};

export const Counter: React.FC<Props> = ({
  from,
  to,
  startFrame = 0,
  durationFrames = 45,
  decimals = 2,
  prefix = "",
  suffix = "",
  signed = false,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = Math.max(0, frame - startFrame);

  // Spring-based progress 0..1 then a simple linear-ish feel at the end
  const progress = spring({
    frame: localFrame,
    fps,
    config: { damping: 18, stiffness: 80, mass: 0.6 },
    durationInFrames: durationFrames,
  });

  const value = interpolate(progress, [0, 1], [from, to]);
  const fixed = value.toFixed(decimals);
  const sign = signed && value >= 0 ? "+" : "";
  return (
    <span style={style}>
      {prefix}
      {sign}
      {fixed}
      {suffix}
    </span>
  );
};
