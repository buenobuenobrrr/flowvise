import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import {
  ArrowDownRight, ArrowUpRight, RefreshCw, Loader2, AlertTriangle,
  CheckCircle2, Building2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  CHART_TOOLTIP_STYLE, CHART_TOOLTIP_LABEL_STYLE,
  CHART_TOOLTIP_ITEM_STYLE, CHART_COLORS,
} from '../lib/chartTheme';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ASSET_CLASSES = [
  { key: 'stocks', label: 'Stocks / ETFs' },
  { key: 'bonds', label: 'Bonds' },
  { key: 'cash', label: 'Cash / Savings' },
  { key: 'real_estate', label: 'Real Estate' },
  { key: 'alternative', label: 'Alternative' },
];

const RISK_OPTIONS = [
  { id: 'conservative', label: 'Conservative' },
  { id: 'moderate', label: 'Moderate' },
  { id: 'aggressive', label: 'Aggressive' },
];

const PortfolioPie = ({ allocation, label }) => {
  const data = ASSET_CLASSES
    .map(a => ({ name: a.label, value: Number(allocation?.[a.key] || 0) }))
    .filter(d => d.value > 0);
  return (
    <Card data-testid={`portfolio-${label.toLowerCase()}-pie`}>
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-base">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[220px]">
          {data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data} cx="50%" cy="50%"
                  innerRadius={50} outerRadius={85}
                  paddingAngle={2} dataKey="value"
                  stroke="hsl(var(--card))" strokeWidth={2}
                >
                  {data.map((entry, i) => (
                    <Cell key={`cell-${entry.name}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={CHART_TOOLTIP_STYLE}
                  labelStyle={CHART_TOOLTIP_LABEL_STYLE}
                  itemStyle={CHART_TOOLTIP_ITEM_STYLE}
                  formatter={(v) => [`${v}%`, 'Allocation']}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
              No allocation
            </div>
          )}
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1.5 mt-3 text-xs">
          {data.map((item, i) => (
            <div key={item.name} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
              <span className="text-muted-foreground">{item.name} {item.value}%</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

const RiskTierPicker = ({ value, onChange }) => (
  <div className="flex gap-2">
    {RISK_OPTIONS.map(opt => (
      <button
        key={opt.id} type="button"
        data-testid={`risk-${opt.id}`}
        onClick={() => onChange(opt.id)}
        className={`flex-1 px-4 py-2 rounded-md text-sm border transition-colors ${
          value === opt.id
            ? 'bg-primary text-primary-foreground border-primary'
            : 'border-border/60 text-muted-foreground hover:border-border hover:text-foreground'
        }`}
      >
        {opt.label}
      </button>
    ))}
  </div>
);

export default function PortfolioPage() {
  const { getAuthHeaders } = useAuth();
  const { fc } = useCurrency();
  const [risk, setRisk] = useState('moderate');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const runAutoDetect = useCallback(async (overrideRisk) => {
    const targetRisk = overrideRisk || risk;
    const showSpinner = result == null ? setLoading : setRefreshing;
    showSpinner(true);
    try {
      const url = new URL(`${API}/portfolio/auto-detect`);
      if (targetRisk) url.searchParams.set('risk_tolerance', targetRisk);
      const res = await fetch(url.toString(), {
        credentials: 'include', headers: getAuthHeaders(),
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) { /* non-json */ }
      if (!res.ok) throw new Error(data.detail || 'Failed to load portfolio');
      setResult(data);
      if (data.risk_tolerance && !overrideRisk) setRisk(data.risk_tolerance);
    } catch (err) {
      toast.error(err.message || 'Failed to load portfolio');
    } finally { setLoading(false); setRefreshing(false); }
  }, [risk, result, getAuthHeaders]);

  // Stable ref to the latest runAutoDetect so the mount-effect can fire it on
  // window/event triggers without re-subscribing every time risk/result change.
  const runAutoDetectRef = useRef(runAutoDetect);
  useEffect(() => { runAutoDetectRef.current = runAutoDetect; }, [runAutoDetect]);

  useEffect(() => {
    runAutoDetectRef.current();
    const onChange = () => runAutoDetectRef.current();
    window.addEventListener('flowvise:data-changed', onChange);
    window.addEventListener('focus', onChange);
    return () => {
      window.removeEventListener('flowvise:data-changed', onChange);
      window.removeEventListener('focus', onChange);
    };
  }, []);

  const handleRiskChange = (newRisk) => {
    setRisk(newRisk);
    runAutoDetect(newRisk);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main className="lg:ml-60 pt-16 lg:pt-0 p-6">
          <div className="max-w-6xl mx-auto space-y-6">
            <Skeleton className="h-10 w-72" />
            <Skeleton className="h-44 rounded-xl" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Skeleton className="h-64 rounded-xl" />
              <Skeleton className="h-64 rounded-xl" />
            </div>
          </div>
        </main>
      </div>
    );
  }

  const noData = !result || result.total_value <= 0 || result.accounts_used === 0;

  return (
    <div className="min-h-screen bg-background" data-testid="portfolio-page">
      <Sidebar />
      <main className="lg:ml-60 pt-16 lg:pt-0 p-6">
        <div className="max-w-6xl mx-auto space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="font-heading text-2xl sm:text-3xl font-semibold tracking-tight">Portfolio Rebalancing</h1>
              <p className="text-muted-foreground mt-1">Pulled from your connected bank accounts and compared against your target risk tier.</p>
            </div>
            <Button variant="outline" onClick={() => runAutoDetect()} disabled={refreshing} data-testid="refresh-portfolio-button">
              {refreshing
                ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Refreshing…</>
                : <><RefreshCw className="w-4 h-4 mr-2" /> Refresh</>}
            </Button>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="font-heading text-base">Target risk tier</CardTitle>
              <CardDescription>Switch tiers to see how your portfolio drifts from a different target.</CardDescription>
            </CardHeader>
            <CardContent>
              <RiskTierPicker value={risk} onChange={handleRiskChange} />
            </CardContent>
          </Card>

          {noData ? (
            <Card data-testid="portfolio-empty-state">
              <CardContent className="py-10 flex flex-col items-center text-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                  <Building2 className="w-6 h-6" />
                </div>
                <div>
                  <p className="font-heading text-lg">No investment-type accounts connected</p>
                  <p className="text-sm text-muted-foreground mt-1 max-w-md">
                    Connect a bank with checking, savings or investment accounts to see your live allocation
                    and rebalancing recommendations.
                  </p>
                </div>
                <Link to="/dashboard/accounts">
                  <Button data-testid="go-link-bank-button">Link a bank account</Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <>
              <Card data-testid="rebalance-summary-card">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-3">
                    {result.needs_rebalance
                      ? <AlertTriangle className="w-5 h-5 text-amber-500" />
                      : <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                    <CardTitle className="font-heading text-lg">
                      {result.needs_rebalance ? 'Rebalancing recommended' : 'Looking good'}
                    </CardTitle>
                  </div>
                  <CardDescription>{result.summary}</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Total portfolio</p>
                    <p className="text-2xl font-heading mt-1">{fc(result.total_value)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Max drift</p>
                    <p className="text-2xl font-heading mt-1">{result.max_drift_pct}%</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Accounts used</p>
                    <p className="text-2xl font-heading mt-1">{result.accounts_used} <span className="text-base text-muted-foreground">of {result.accounts_seen}</span></p>
                  </div>
                </CardContent>
              </Card>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <PortfolioPie allocation={result.current_allocation} label="Current" />
                <PortfolioPie allocation={result.target_allocation} label="Target" />
              </div>

              {result.counted_accounts?.length > 0 && (
                <Card data-testid="counted-accounts-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="font-heading text-base">Counted accounts</CardTitle>
                    <CardDescription>How each account maps to an asset class.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="rounded-lg border border-border/60 divide-y divide-border/60 text-sm">
                      {result.counted_accounts.map(a => (
                        <div key={a.account_id} className="flex justify-between px-4 py-2.5">
                          <span>{a.name} <span className="text-muted-foreground">· {a.type}</span></span>
                          <span className="text-muted-foreground capitalize">{a.asset_class.replace('_', ' ')} · {fc(a.balance)}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {result.moves.length > 0 && (
                <Card data-testid="rebalance-moves-card">
                  <CardHeader>
                    <CardTitle className="font-heading">Suggested moves</CardTitle>
                    <CardDescription>Apply these to align with the {result.risk_tolerance} target.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="divide-y divide-border/60">
                      {result.moves.map(m => (
                        <div key={m.asset_class} className="flex items-center justify-between py-3 gap-4" data-testid={`move-${m.asset_class}`}>
                          <div className="flex items-center gap-3">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                              m.action === 'buy' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'
                            }`}>
                              {m.action === 'buy' ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                            </div>
                            <div>
                              <p className="font-medium capitalize">{m.asset_class.replace('_', ' ')}</p>
                              <p className="text-xs text-muted-foreground">
                                {m.current_pct}% → {m.target_pct}% &nbsp;·&nbsp; {fc(m.current_value)} → {fc(m.target_value)}
                              </p>
                            </div>
                          </div>
                          <div className={`text-right font-heading text-base ${m.action === 'buy' ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {m.action === 'buy' ? '+' : ''}{fc(m.delta)}
                          </div>
                        </div>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-4">
                      Educational guidance only. Tax events, transaction costs, and bid-ask spreads aren't modeled here.
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
