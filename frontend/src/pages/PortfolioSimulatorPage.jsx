import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Switch } from '../components/ui/switch';
import { Slider } from '../components/ui/slider';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts';
import {
  Calculator, TrendingUp, BarChart3, Loader2, AlertTriangle, Info, Sparkles
} from 'lucide-react';
import { formatCurrency, cn } from '../lib/utils';
import { useCurrency } from '../contexts/CurrencyContext';
import { toast } from 'sonner';
import {
  CHART_AXIS_TICK, CHART_TOOLTIP_STYLE, CHART_TOOLTIP_LABEL_STYLE,
  CHART_TOOLTIP_ITEM_STYLE, CHART_GRID_STROKE, CHART_AXIS_STROKE
} from '../lib/chartTheme';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const MIN_PROFIT_PROBABILITY = 70;

const RISK_PRESETS = {
  conservative: { return: 0.04, volatility: 0.08, label: 'Conservative (4% / 8% vol)' },
  moderate: { return: 0.07, volatility: 0.15, label: 'Moderate (7% / 15% vol)' },
  aggressive: { return: 0.11, volatility: 0.22, label: 'Aggressive (11% / 22% vol)' }
};

export default function PortfolioSimulatorPage() {
  const { getAuthHeaders } = useAuth();
  const { fc, symbol } = useCurrency();
  const [advancedMode, setAdvancedMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [simpleResult, setSimpleResult] = useState(null);
  const [monteCarloResult, setMonteCarloResult] = useState(null);

  // Simple mode form
  const [simpleForm, setSimpleForm] = useState({
    initial_investment: 5000,
    monthly_contribution: 200,
    years: 10,
    risk_level: 'moderate'
  });

  // Advanced mode form
  const [advForm, setAdvForm] = useState({
    initial_investment: 5000,
    monthly_contribution: 200,
    years: 10,
    expected_return: 0.07,
    volatility: 0.15,
    simulations: 500
  });

  const handleSimple = async () => {
    setLoading(true);
    setSimpleResult(null);
    try {
      const preset = RISK_PRESETS[simpleForm.risk_level];
      const res = await fetch(`${API}/simulation/simple`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({
          ...simpleForm,
          expected_return: preset.return
        })
      });
      if (!res.ok) throw new Error();
      setSimpleResult(await res.json());
    } catch (err) {
      toast.error('Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleMonteCarlo = async () => {
    setLoading(true);
    setMonteCarloResult(null);
    try {
      const res = await fetch(`${API}/simulation/monte-carlo`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify(advForm)
      });
      if (!res.ok) throw new Error();
      setMonteCarloResult(await res.json());
    } catch (err) {
      toast.error('Monte Carlo simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRiskPreset = (level) => {
    setSimpleForm({ ...simpleForm, risk_level: level });
    const p = RISK_PRESETS[level];
    setAdvForm({ ...advForm, expected_return: p.return, volatility: p.volatility });
  };

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="lg:ml-60 pt-16 lg:pt-0 p-6" data-testid="portfolio-simulator-page">
        <div className="max-w-6xl mx-auto space-y-6">

          {/* Header */}
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-semibold tracking-tight flex items-center gap-3">
              <Calculator className="w-8 h-8 text-primary" />
              Portfolio Simulator
            </h1>
            <p className="text-muted-foreground mt-1">
              "What if I invest EUR X in Y?" — Project your potential returns
            </p>
          </div>

          {/* Mode Toggle */}
          <div className="flex items-center gap-3">
            <span className={cn("text-sm", !advancedMode && "font-medium")}>Simple</span>
            <Switch checked={advancedMode} onCheckedChange={setAdvancedMode} data-testid="advanced-mode-toggle" />
            <span className={cn("text-sm", advancedMode && "font-medium")}>Advanced (Monte Carlo)</span>
          </div>

          {/* Input Card */}
          <Card data-testid="simulation-input-card">
            <CardHeader>
              <CardTitle className="font-heading">
                {advancedMode ? 'Monte Carlo Simulation' : 'Investment Projection'}
              </CardTitle>
              <CardDescription>
                {advancedMode
                  ? 'Runs hundreds of random scenarios to show best/worst/average outcomes'
                  : 'Simple compound growth projection based on expected returns'
                }
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Initial Investment (EUR)</Label>
                  <Input
                    data-testid="initial-investment-input"
                    type="number"
                    step="500"
                    value={advancedMode ? advForm.initial_investment : simpleForm.initial_investment}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value) || 0;
                      if (advancedMode) setAdvForm({ ...advForm, initial_investment: v });
                      else setSimpleForm({ ...simpleForm, initial_investment: v });
                    }}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Monthly Contribution (EUR)</Label>
                  <Input
                    data-testid="monthly-contribution-input"
                    type="number"
                    step="50"
                    value={advancedMode ? advForm.monthly_contribution : simpleForm.monthly_contribution}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value) || 0;
                      if (advancedMode) setAdvForm({ ...advForm, monthly_contribution: v });
                      else setSimpleForm({ ...simpleForm, monthly_contribution: v });
                    }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Time Horizon: {advancedMode ? advForm.years : simpleForm.years} years</Label>
                <Slider
                  value={[advancedMode ? advForm.years : simpleForm.years]}
                  onValueChange={([v]) => {
                    if (advancedMode) setAdvForm({ ...advForm, years: v });
                    else setSimpleForm({ ...simpleForm, years: v });
                  }}
                  min={1} max={40} step={1}
                  data-testid="years-slider"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>1 year</span><span>40 years</span>
                </div>
              </div>

              {!advancedMode ? (
                <div className="space-y-2">
                  <Label>Risk Level</Label>
                  <Select value={simpleForm.risk_level} onValueChange={handleRiskPreset}>
                    <SelectTrigger data-testid="risk-level-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(RISK_PRESETS).map(([k, v]) => (
                        <SelectItem key={k} value={k}>{v.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label>Expected Annual Return (%)</Label>
                    <Input
                      data-testid="return-input"
                      type="number" step="0.5"
                      value={(advForm.expected_return * 100).toFixed(1)}
                      onChange={(e) => setAdvForm({ ...advForm, expected_return: parseFloat(e.target.value) / 100 || 0 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Annual Volatility (%)</Label>
                    <Input
                      data-testid="volatility-input"
                      type="number" step="0.5"
                      value={(advForm.volatility * 100).toFixed(1)}
                      onChange={(e) => setAdvForm({ ...advForm, volatility: parseFloat(e.target.value) / 100 || 0 })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Simulations</Label>
                    <Input
                      data-testid="simulations-input"
                      type="number" step="100" min="100" max="1000"
                      value={advForm.simulations}
                      onChange={(e) => setAdvForm({ ...advForm, simulations: parseInt(e.target.value) || 500 })}
                    />
                  </div>
                </div>
              )}

              <Button
                onClick={advancedMode ? handleMonteCarlo : handleSimple}
                disabled={loading}
                className="btn-lift"
                data-testid="run-simulation-button"
              >
                {loading ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Running...</>
                ) : (
                  <><Sparkles className="w-4 h-4 mr-2" />{advancedMode ? 'Run Monte Carlo' : 'Calculate'}</>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Simple Result */}
          {simpleResult && !advancedMode && (
            <Card data-testid="simple-result-card">
              <CardHeader>
                <CardTitle className="font-heading">Projection Results</CardTitle>
                <CardDescription>Compound growth over {simpleResult.summary.years} years at {simpleResult.summary.annual_return.toFixed(1)}% annual return</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Final Balance</p>
                    <p className="text-xl font-semibold font-heading text-primary">{fc(simpleResult.summary.final_balance)}</p>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Total Invested</p>
                    <p className="text-xl font-semibold font-heading">{fc(simpleResult.summary.total_invested)}</p>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Total Gains</p>
                    <p className="text-xl font-semibold font-heading text-green-600">{fc(simpleResult.summary.total_gains)}</p>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Total Return</p>
                    <p className="text-xl font-semibold font-heading">{simpleResult.summary.return_pct}%</p>
                  </div>
                </div>

                {/* Chart */}
                <div className="h-[350px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={simpleResult.timeline}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                      <XAxis dataKey="year" stroke={CHART_AXIS_STROKE} tick={CHART_AXIS_TICK} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}y`} />
                      <YAxis stroke={CHART_AXIS_STROKE} tick={CHART_AXIS_TICK} tickLine={false} axisLine={false} width={60} tickFormatter={(v) => `${symbol}${(v/1000).toFixed(0)}k`} />
                      <Tooltip
                        contentStyle={CHART_TOOLTIP_STYLE}
                        labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                        itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                        formatter={(value, name) => [fc(value), name === 'balance' ? 'Balance' : 'Invested']}
                        labelFormatter={(v) => `Year ${v}`}
                      />
                      <Area type="monotone" dataKey="invested" stackId="1" fill="hsl(var(--muted))" stroke="hsl(var(--muted-foreground))" fillOpacity={0.3} name="invested" />
                      <Area type="monotone" dataKey="balance" fill="hsl(var(--primary))" stroke="hsl(var(--primary))" fillOpacity={0.15} name="balance" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Monte Carlo Result */}
          {monteCarloResult && advancedMode && (
            <Card data-testid="monte-carlo-result-card">
              <CardHeader>
                <CardTitle className="font-heading">Monte Carlo Results</CardTitle>
                <CardDescription>
                  {monteCarloResult.summary.simulations_run} scenarios simulated over {monteCarloResult.summary.years} years
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <div className="p-3 bg-red-50 rounded-lg text-center">
                    <p className="text-xs text-muted-foreground">Worst (5th)</p>
                    <p className="font-semibold text-red-600">{fc(monteCarloResult.summary.worst_case)}</p>
                  </div>
                  <div className="p-3 bg-amber-50 rounded-lg text-center">
                    <p className="text-xs text-muted-foreground">10th Percentile</p>
                    <p className="font-semibold text-amber-600">{fc(monteCarloResult.summary.p10)}</p>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg text-center">
                    <p className="text-xs text-muted-foreground">Median (50th)</p>
                    <p className="font-semibold text-blue-600">{fc(monteCarloResult.summary.median)}</p>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg text-center">
                    <p className="text-xs text-muted-foreground">90th Percentile</p>
                    <p className="font-semibold text-green-600">{fc(monteCarloResult.summary.p90)}</p>
                  </div>
                  <div className="p-3 bg-emerald-50 rounded-lg text-center">
                    <p className="text-xs text-muted-foreground">Best (95th)</p>
                    <p className="font-semibold text-emerald-600">{fc(monteCarloResult.summary.best_case)}</p>
                  </div>
                </div>

                {/* Key metrics */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Total Invested</p>
                    <p className="font-semibold">{fc(monteCarloResult.summary.total_invested)}</p>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Probability of Profit</p>
                    <p className={cn(
                      "font-semibold",
                      monteCarloResult.summary.probability_of_profit >= MIN_PROFIT_PROBABILITY ? 'text-green-600' : 'text-amber-600'
                    )}>
                      {monteCarloResult.summary.probability_of_profit}%
                    </p>
                  </div>
                  <div className="p-4 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Volatility</p>
                    <p className="font-semibold">{monteCarloResult.summary.volatility_pct}%</p>
                  </div>
                </div>

                {/* Fan Chart */}
                <div className="h-[400px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={monteCarloResult.percentile_timeline}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID_STROKE} />
                      <XAxis dataKey="year" stroke={CHART_AXIS_STROKE} tick={CHART_AXIS_TICK} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}y`} />
                      <YAxis stroke={CHART_AXIS_STROKE} tick={CHART_AXIS_TICK} tickLine={false} axisLine={false} width={60} tickFormatter={(v) => `${symbol}${(v/1000).toFixed(0)}k`} />
                      <Tooltip
                        contentStyle={CHART_TOOLTIP_STYLE}
                        labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                        itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                        formatter={(value, name) => {
                          const labels = { p10: '10th %ile (Bad)', p25: '25th %ile', p50: 'Median', p75: '75th %ile', p90: '90th %ile (Good)' };
                          return [fc(value), labels[name] || name];
                        }}
                        labelFormatter={(v) => `Year ${v}`}
                      />
                      <Area type="monotone" dataKey="p10" fill="hsl(15, 45%, 55%)" stroke="none" fillOpacity={0.08} />
                      <Area type="monotone" dataKey="p25" fill="hsl(45, 40%, 60%)" stroke="none" fillOpacity={0.1} />
                      <Area type="monotone" dataKey="p75" fill="hsl(150, 30%, 40%)" stroke="none" fillOpacity={0.1} />
                      <Area type="monotone" dataKey="p90" fill="hsl(150, 30%, 30%)" stroke="none" fillOpacity={0.08} />
                      <Line type="monotone" dataKey="p50" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                <div className="flex flex-wrap gap-3 text-xs">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: 'hsl(15, 45%, 55%, 0.3)' }} />
                    <span className="text-muted-foreground">10th-90th percentile range</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-primary" />
                    <span className="text-muted-foreground">Median outcome</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Disclaimer */}
          <div className="disclaimer-banner p-4 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm">
                <p className="font-medium text-amber-800">Simulation Disclaimer</p>
                <p className="text-amber-700 mt-1">
                  These projections are hypothetical and for educational purposes only. Actual returns will vary.
                  Past performance does not guarantee future results. All investments carry risk.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
