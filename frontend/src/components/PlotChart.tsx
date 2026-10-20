import { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';
import type { PlotlyTrace } from '../api/types';

interface Props {
  data: PlotlyTrace[];
  layout: Record<string, unknown>;
}

export default function PlotChart({ data, layout }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const finalLayout = {
      ...layout,
      autosize: true,
      margin: { l: 50, r: 20, t: 50, b: 60 },
    };
    const config = { responsive: true, displaylogo: false };

    Plotly.react(container, data, finalLayout, config);

    return () => {
      Plotly.purge(container);
    };
  }, [data, layout]);

  return <div ref={containerRef} className="h-96 w-full" />;
}
