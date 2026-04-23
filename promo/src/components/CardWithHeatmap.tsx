import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS, FONTS } from "../lib/constants";

type Props = {
  cardPath: string;
  heatmapPath: string;
  name: string;
  price: number;
  startFrame: number;
  durationFrames: number;
};

export const CardWithHeatmap: React.FC<Props> = ({
  cardPath,
  heatmapPath,
  name,
  price,
  startFrame,
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - startFrame;

  // Hide entirely outside window
  if (localFrame < -5 || localFrame > durationFrames + 10) {
    return null;
  }

  const enter = spring({
    frame: localFrame,
    fps,
    config: { damping: 18, stiffness: 120 },
    durationInFrames: 18,
  });

  const exit = interpolate(
    localFrame,
    [durationFrames - 10, durationFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const opacity = enter * exit;
  const translateX = interpolate(enter, [0, 1], [120, 0]);
  const scale = interpolate(enter, [0, 1], [0.92, 1]);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 36,
        opacity,
        transform: `translateX(${translateX}px) scale(${scale})`,
      }}
    >
      {/* Card + brain side-by-side */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 48,
        }}
      >
        <div
          style={{
            width: 360,
            height: 504,
            overflow: "hidden",
            borderRadius: 16,
            boxShadow: "0 10px 40px rgba(0,0,0,0.6)",
            background: "#000",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Img
            src={staticFile(cardPath)}
            style={{
              maxWidth: "100%",
              maxHeight: "100%",
              objectFit: "contain",
            }}
          />
        </div>
        <div
          style={{
            fontSize: 48,
            color: COLORS.fgMuted,
            fontFamily: FONTS.mono,
            width: 48,
            textAlign: "center",
          }}
        >
          →
        </div>
        <div
          style={{
            width: 360,
            height: 360,
            background: "#000",
            borderRadius: 16,
            boxShadow: "0 10px 40px rgba(0,0,0,0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}
        >
          <Img
            src={staticFile(heatmapPath)}
            style={{
              maxWidth: "120%",
              maxHeight: "140%",
              objectFit: "contain",
            }}
          />
        </div>
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: COLORS.fg,
            fontFamily: FONTS.sans,
            fontWeight: 700,
            maxWidth: 800,
            textAlign: "center",
          }}
        >
          {name}
        </div>
        <div
          style={{
            fontSize: 36,
            color: COLORS.accentYellow,
            fontFamily: FONTS.mono,
            fontWeight: 700,
          }}
        >
          ${price.toFixed(2)}
        </div>
      </div>
    </div>
  );
};
