import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { FPS, TOTAL_DURATION, dimsFor, Orientation } from "./lib/constants";
import { Main, MainProps } from "./Main";

const calculateMetadata: CalculateMetadataFunction<MainProps> = ({ props }) => {
  const { width, height } = dimsFor(props.orientation);
  return {
    width,
    height,
    props,
    fps: FPS,
    durationInFrames: TOTAL_DURATION,
  };
};

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="Main"
        component={Main}
        defaultProps={{ orientation: "vertical" as Orientation }}
        calculateMetadata={calculateMetadata}
        // Placeholder dims — overridden by calculateMetadata
        width={1080}
        height={1920}
        fps={FPS}
        durationInFrames={TOTAL_DURATION}
      />
    </>
  );
};
