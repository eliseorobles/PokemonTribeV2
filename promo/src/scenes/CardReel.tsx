import React from "react";
import { Sequence, interpolate, useCurrentFrame } from "remotion";
import { COLORS, FONTS } from "../lib/constants";
import { CardWithHeatmap } from "../components/CardWithHeatmap";
import { useStats } from "../lib/stats";

const PER_CARD_FRAMES = 22; // ~0.73 s each → 7 cards ≈ 154 frames

export const CardReel: React.FC = () => {
  const frame = useCurrentFrame();
  const stats = useStats();

  const tickerOpacity = interpolate(frame, [0, 15, 140, 150], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  if (!stats) {
    return null;
  }

  const cards = stats.cards.slice(0, 7);

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      {/* Ticker strip */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
          fontFamily: FONTS.mono,
          color: COLORS.fgDim,
          fontSize: 24,
          letterSpacing: 2,
          textTransform: "uppercase",
          opacity: tickerOpacity,
        }}
      >
        213 cards &nbsp;→&nbsp; TRIBE v2 &nbsp;→&nbsp; predicted fMRI
      </div>

      {cards.map((c, i) => (
        <Sequence
          key={c.id}
          from={i * PER_CARD_FRAMES}
          durationInFrames={PER_CARD_FRAMES + 6}
          layout="none"
        >
          <CardWithHeatmap
            cardPath={c.card_path}
            heatmapPath={c.heatmap_path}
            name={c.name}
            price={c.price}
            startFrame={0}
            durationFrames={PER_CARD_FRAMES + 6}
          />
        </Sequence>
      ))}
    </div>
  );
};
