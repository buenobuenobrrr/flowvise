import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import {
  CHART_AXIS_TICK, CHART_TOOLTIP_STYLE, CHART_TOOLTIP_LABEL_STYLE,
  CHART_TOOLTIP_ITEM_STYLE, CHART_COLORS, CHART_GRID_STROKE, CHART_AXIS_STROKE
} from '../lib/chartTheme';

const BAR_RADIUS = [6, 6, 0, 0];

export function SpendingCategoryChart({ data, fc }) {
  return (
    <Card data-testid="category-pie-chart">
      <CardHeader>
        <CardTitle className="font-heading">Spending by Category</CardTitle>
        <CardDescription>Where your money goes</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          {data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="hsl(var(--card))"
                  strokeWidth={2}
                >
                  {data.map((_, index) => (
                    <Cell key={`cell-cat-${data[index]?.name || index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={CHART_TOOLTIP_STYLE}
                  labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                  itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                  formatter={(value) => [fc(value), 'Amount']}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <p>No spending data yet</p>
            </div>
          )}
        </div>
        {data.length > 0 && (
          <div className="flex flex-wrap gap-x-4 gap-y-2 mt-4 px-2 text-xs">
            {data.slice(0, 8).map((item, index) => (
              <div key={item.name} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }} />
                <span className="text-muted-foreground truncate max-w-[140px]">{item.name}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function MonthlySpendingChart({ data, fc, symbol }) {
  return (
    <Card data-testid="monthly-bar-chart">
      <CardHeader>
        <CardTitle className="font-heading">Monthly Spending</CardTitle>
        <CardDescription>Last 6 months</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          {data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                <XAxis
                  dataKey="month"
                  stroke={CHART_AXIS_STROKE}
                  tick={CHART_AXIS_TICK}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke={CHART_AXIS_STROKE}
                  tick={CHART_AXIS_TICK}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `${symbol}${value}`}
                  width={60}
                />
                <Tooltip
                  contentStyle={CHART_TOOLTIP_STYLE}
                  labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                  itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                  formatter={(value) => [fc(value), 'Spending']}
                  cursor={{ fill: CHART_AXIS_STROKE, fillOpacity: 0.08 }}
                />
                <Bar dataKey="amount" fill="hsl(var(--primary))" radius={BAR_RADIUS} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              <p>No monthly data yet</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
