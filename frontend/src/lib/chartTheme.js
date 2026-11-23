// Shared chart theme constants so axis labels, tooltip text, and grid lines
// adapt to dark/light mode. Recharts `stroke` only colors the axis line —
// the actual tick text needs an explicit `tick.fill`.

export const CHART_AXIS_TICK = {
  fill: 'hsl(var(--muted-foreground))',
  fontSize: 12,
};

export const CHART_TOOLTIP_STYLE = {
  background: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '10px',
  boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
  fontSize: '13px',
  color: 'hsl(var(--foreground))',
};

export const CHART_TOOLTIP_LABEL_STYLE = {
  color: 'hsl(var(--foreground))',
  fontWeight: 600,
  marginBottom: 4,
};

export const CHART_TOOLTIP_ITEM_STYLE = {
  color: 'hsl(var(--foreground))',
};

export const CHART_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899',
  '#06b6d4', '#f97316', '#6366f1', '#14b8a6', '#64748b',
];

export const CHART_GRID_STROKE = 'hsl(var(--border))';
export const CHART_AXIS_STROKE = 'hsl(var(--muted-foreground))';
