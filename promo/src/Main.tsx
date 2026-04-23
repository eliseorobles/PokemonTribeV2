import React from "react";
import { AbsoluteFill, Series } from "remotion";
import {
  COLORS,
  CARD_REEL_DURATION,
  CTA_DURATION,
  INTRO_DURATION,
  Orientation,
  SAFE_H,
  SAFE_W,
  STAT_REVEAL_DURATION,
  TOP_REGION_DURATION,
  safeTopFor,
} from "./lib/constants";
import { Intro } from "./scenes/Intro";
import { CardReel } from "./scenes/CardReel";
import { StatReveal } from "./scenes/StatReveal";
import { TopRegion } from "./scenes/TopRegion";
import { CTA } from "./scenes/CTA";

export type MainProps = {
  orientation: Orientation;
};

export const Main: React.FC<MainProps> = ({ orientation }) => {
  const safeTop = safeTopFor(orientation);

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
      }}
    >
      {/* Soft gradient edges visible only in vertical (dead space) */}
      {orientation === "vertical" && (
        <AbsoluteFill
          style={{
            background:
              `linear-gradient(180deg, ${COLORS.bgElev} 0%, ${COLORS.bg} 20%, ${COLORS.bg} 80%, ${COLORS.bgElev} 100%)`,
          }}
        />
      )}

      {/* Safe 1080x1080 content area */}
      <AbsoluteFill
        style={{
          top: safeTop,
          height: SAFE_H,
          width: SAFE_W,
        }}
      >
        <Series>
          <Series.Sequence durationInFrames={INTRO_DURATION}>
            <Intro />
          </Series.Sequence>
          <Series.Sequence durationInFrames={CARD_REEL_DURATION}>
            <CardReel />
          </Series.Sequence>
          <Series.Sequence durationInFrames={STAT_REVEAL_DURATION}>
            <StatReveal />
          </Series.Sequence>
          <Series.Sequence durationInFrames={TOP_REGION_DURATION}>
            <TopRegion />
          </Series.Sequence>
          <Series.Sequence durationInFrames={CTA_DURATION}>
            <CTA />
          </Series.Sequence>
        </Series>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
