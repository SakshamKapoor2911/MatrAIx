import { useEffect, useState } from "react";

const GAP_PX = 10;
const MIN_CARD_WIDTH = 124;
const MIN_CARD_HEIGHT = 72;

export type BatchGridLayout = {
  cols: number;
  rows: number;
  scroll: boolean;
  rowHeight: number;
};

export function computeBatchGridLayout(
  count: number,
  width: number,
  height: number,
): BatchGridLayout {
  if (count <= 0 || width <= 0 || height <= 0) {
    return { cols: 1, rows: 1, scroll: false, rowHeight: 72 };
  }

  const maxCols = Math.max(
    1,
    Math.min(count, Math.floor((width + GAP_PX) / (MIN_CARD_WIDTH + GAP_PX))),
  );

  let best: { cols: number; rows: number; rowHeight: number; score: number } | null = null;

  for (let cols = 1; cols <= maxCols; cols += 1) {
    const rows = Math.ceil(count / cols);
    const cellW = (width - (cols - 1) * GAP_PX) / cols;
    const rowHeight = (height - (rows - 1) * GAP_PX) / rows;
    if (rowHeight < MIN_CARD_HEIGHT || cellW < MIN_CARD_WIDTH) continue;

    const waste = cols * rows - count;
    const score = rowHeight * cellW - waste * 400;
    if (!best || score > best.score) {
      best = { cols, rows, rowHeight, score };
    }
  }

  if (best) {
    return {
      cols: best.cols,
      rows: best.rows,
      scroll: false,
      rowHeight: best.rowHeight,
    };
  }

  const cols = Math.max(1, Math.min(maxCols, count > 60 ? maxCols : Math.min(4, maxCols)));
  const rows = Math.ceil(count / cols);
  const contentHeight = rows * MIN_CARD_HEIGHT + (rows - 1) * GAP_PX;
  return {
    cols,
    rows,
    scroll: contentHeight > height + 1,
    rowHeight: MIN_CARD_HEIGHT,
  };
}

export function useBatchGridLayout(count: number) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const [layout, setLayout] = useState<BatchGridLayout>(() =>
    computeBatchGridLayout(count, 480, 320),
  );

  useEffect(() => {
    if (!container) return;

    const measure = () => {
      const rect = container.getBoundingClientRect();
      setLayout(computeBatchGridLayout(count, rect.width, rect.height));
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);
    return () => observer.disconnect();
  }, [container, count]);

  return { setContainer, layout };
}
