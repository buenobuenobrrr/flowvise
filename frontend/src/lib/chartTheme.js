// Shared chart theme. Soft fills, thin lines, warm neutrals.
// Recharts `stroke` only colors the axis line — tick text needs `tick.fill`.

export const CHART_AXIS_TICK = {
  fill: 'hsl(var(--muted-foreground))',
  fontSize: 12,
  fontFamily: 'Outfit, system-ui, sans-serif',
};

export const CHART_TOOLTIP_STYLE = {
  background: 'hsl(var(--card))',
  border: '1px solid hsl(var(--border))',
  borderRadius: '14px',
  boxShadow: '0 10px 30px rgba(40, 36, 30, 0.08)',
  fontSize: '13px',
  color: 'hsl(var(--foreground))',
  padding: '10px 12px',
};

export const CHART_TOOLTIP_LABEL_STYLE = {
  color: 'hsl(var(--muted-foreground))',
  fontWeight: 500,
  marginBottom: 4,
};

export const CHART_TOOLTIP_ITEM_STYLE = {
  color: 'hsl(var(--foreground))',
  padding: 0,
};

export const CHART_COLORS = [
  '#1E3A5F',
  '#C4622D',
  '#5C6B7A',
  '#C47B5A',
  '#3D6F8F',
  '#8A6A4F',
  '#4C5D73',
  '#D4A574',
  '#6E4B3A',
  '#7A8EA3',
];

export const CHART_GRID_STROKE = 'hsl(var(--border))';
export const CHART_AXIS_STROKE = 'hsl(var(--muted-foreground))';
export const CHART_LINE = 'hsl(var(--primary))';
