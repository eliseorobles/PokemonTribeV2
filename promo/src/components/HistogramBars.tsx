import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../lib/constants";

/**
 * Renders a ~32-bar null distribution histogram that grows in over time.
 * The "real R²" spike is a tall, bright yellow bar far to the right.
 */
type Props = {
  startFrame?: number;
  growFrames?: number;
  realR2?: number;
  width?: number;
  height?: number;
};

// Normal-ish distribution centered at 0 (the null shuffle distribution)
const NULL_COUNTS = [
  1, 0, 1, 2, 1, 2, 3, 5, 8, 14, 22, 33, 42, 46, 43, 35,
  26, 18, 10, 6, 3, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0,
];

export const HistogramBars: React.FC<Props> = ({
  startFrame = 0,
  growFrames = 60,
  realR2 = 0.095,
  width = 900,
  height = 380,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = Math.max(0, frame - startFrame);

  const barWidth = (width / NULL_COUNTS.length) * 0.8;
  const barGap = (width / NULL_COUNTS.length) * 0.2;
  const maxCount = Math.max(...NULL_COUNTS);

  // Grow each bar sequentially
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ overflow: "visible" }}
    >
      {/* X axis line */}
      <line
        x1={0}
        x2={width}
        y1={height - 20}
        y2={height - 20}
        stroke={COLORS.line}
        strokeWidth={2}
      />
      {/* Null bars */}
      {NULL_COUNTS.map((c, i) => {
        const barStart = startFrame + i * (growFrames / NULL_COUNTS.length) * 0.5;
        const localBarFrame = Math.max(0, frame - barStart);
        const grow = spring({
          frame: localBarFrame,
          fps,
          config: { damping: 20, stiffness: 100 },
          durationInFrames: 12,
        });
        const targetH = (c / maxCount) * (height - 40);
        const h = targetH * grow;
        const x = i * (barWidth + barGap);
        const y = height - 20 - h;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={barWidth}
            height={h}
            fill={COLORS.fgDim}
            opacity={0.55}
            rx={1.5}
          />
        );
      })}
      {/* Zero marker */}
      <line
        x1={width * 0.31}
        x2={width * 0.31}
        y1={10}
        y2={height - 20}
        stroke={COLORS.fgMuted}
        strokeWidth={1.5}
        strokeDasharray="5 5"
        opacity={0.5}
      />
      {/* Real R² spike — animates in after nulls */}
      <RealBar
        startFrame={startFrame + growFrames * 0.7}
        width={width}
        height={height}
        realR2={realR2}
      />
    </svg>
  );
};

const RealBar: React.FC<{
  startFrame: number;
  width: number;
  height: number;
  realR2: number;
}> = ({ startFrame, width, height, realR2 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = Math.max(0, frame - startFrame);

  const grow = spring({
    frame: localFrame,
    fps,
    config: { damping: 14, stiffness: 140 },
    durationInFrames: 18,
  });

  const x = width * 0.95;
  const barW = 16;
  const barH = (height - 40) * 0.95 * grow;
  const y = height - 20 - barH;

  const glow = interpolate(localFrame, [0, 30], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <g>
      {/* Glow halo */}
      <rect
        x={x - barW / 2 - 6}
        y={y - 6}
        width={barW + 12}
        height={barH + 12}
        fill={COLORS.accentYellow}
        opacity={glow * 0.25}
        rx={6}
      />
      <rect
        x={x - barW / 2}
        y={y}
        width={barW}
        height={barH}
        fill={COLORS.accentYellow}
        rx={2}
      />
      {/* Label above the bar */}
      <text
        x={x}
        y={y - 14}
        fill={COLORS.accentYellow}
        fontSize={22}
        fontFamily="monospace"
        fontWeight="bold"
        textAnchor="middle"
        opacity={glow}
      >
        R² = +{realR2.toFixed(3)}
      </text>
    </g>
  );
};
