import { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

export type Stats = {
  n_cards: number;
  n_rois: number;
  r2_real: number;
  r2_null_mean: number;
  r2_null_p95: number;
  percentile_in_null: number;
  top_roi: string;
  top_roi_r: number;
  total_value: number;
  cards: Array<{
    id: string;
    name: string;
    price: number;
    card_path: string;
    heatmap_path: string;
  }>;
};

export const useStats = (): Stats | null => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [handle] = useState(() => delayRender("Loading stats.json"));

  useEffect(() => {
    fetch(staticFile("stats.json"))
      .then((r) => r.json())
      .then((data: Stats) => {
        setStats(data);
        continueRender(handle);
      })
      .catch((err) => {
        console.error("Failed to load stats.json", err);
        continueRender(handle);
      });
  }, [handle]);

  return stats;
};
