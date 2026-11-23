import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Button } from './ui/button';
import { Separator } from './ui/separator';
import {
  Popover, PopoverContent, PopoverTrigger,
} from './ui/popover';
import {
  Wallet, TrendingDown, PiggyBank, AlertTriangle, ArrowRight, Shield, TrendingUp,
  Activity, Snowflake, Eye, Info, ChevronRight
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Link } from 'react-router-dom';

function SviGauge({ svi }) {
  const pct = Math.min(svi * 100, 100);
  const label = svi < 0.15 ? 'Stable' : svi < 0.35 ? 'Moderate' : svi < 0.6 ? 'Volatile' : 'Erratic';
  const color = svi < 0.15 ? 'text-green-600' : svi < 0.35 ? 'text-amber-500' : 'text-destructive';
  return (
    <div data-testid="svi-gauge">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-muted-foreground">Spending Volatility</span>
        <span className={cn("font-medium", color)}>{label} ({svi.toFixed(2)})</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: svi < 0.15 ? 'hsl(150,50%,40%)' : svi < 0.35 ? 'hsl(40,90%,50%)' : 'hsl(0,70%,50%)' }} />
      </div>
    </div>
  );
}

export function StatsCards({ totalBalance, accounts, spendingData, readinessData, fc, t, getStatusColor }) {
  const sviData = readinessData?.svi;
  const svi = sviData?.svi || 0;
  const elasticBuffer = readinessData?.elastic_buffer;
  const spikeInfo = readinessData?.spike_detection;
  const safeEngine = readinessData?.safe_to_invest_engine;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card className="card-hover" data-testid="total-balance-card">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{t('total_balance')}</CardTitle>
          <Wallet className="w-5 h-5 text-primary" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-semibold font-heading">{fc(totalBalance)}</div>
          <p className="text-xs text-muted-foreground mt-1">{accounts.length} account{accounts.length !== 1 ? 's' : ''} connected</p>
        </CardContent>
      </Card>

      <Card className="card-hover" data-testid="monthly-spending-card">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{t('avg_monthly_spending')}</CardTitle>
          <TrendingDown className="w-5 h-5 text-destructive" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-semibold font-heading">{fc(spendingData?.average_monthly_spending || 0)}</div>
          <p className="text-xs text-muted-foreground mt-1">Based on {spendingData?.transaction_count || 0} transactions</p>
        </CardContent>
      </Card>

      <Card className={cn("card-hover", safeEngine?.frozen && "border-blue-400/50")} data-testid="safe-to-invest-card">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">{t('safe_to_invest')}</CardTitle>
          {safeEngine?.frozen ? <Snowflake className="w-5 h-5 text-blue-500" /> : <PiggyBank className="w-5 h-5 text-accent" />}
        </CardHeader>
        <CardContent>
          <Popover>
            <PopoverTrigger asChild>
              <button className="w-full text-left group cursor-pointer" data-testid="safe-to-invest-trigger">
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-semibold font-heading">{fc(readinessData?.safe_to_invest || 0)}</span>
                  <Info className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                {safeEngine?.frozen ? (
                  <p className="text-xs text-blue-600 mt-1" data-testid="cooling-off-notice">Cooling off — spending spike detected</p>
                ) : (
                  <div className="flex items-center gap-2 mt-1">
                    <Badge className={cn(getStatusColor(readinessData?.status))}>{readinessData?.status?.replace('_', ' ') || 'Unknown'}</Badge>
                    {safeEngine && !safeEngine.frozen && (
                      <span className="text-[10px] text-muted-foreground flex items-center gap-0.5" data-testid="shadow-buffer-badge">
                        <Eye className="w-3 h-3" />{Math.round(safeEngine.shadow_buffer_pct * 100)}% shown
                      </span>
                    )}
                  </div>
                )}
                <p className="text-[10px] text-primary mt-1.5 flex items-center gap-0.5 opacity-60 group-hover:opacity-100 transition-opacity">
                  <ChevronRight className="w-3 h-3" />Click for reasoning
                </p>
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-80" align="start" data-testid="safe-to-invest-reasoning">
              <div className="space-y-3">
                <p className="font-medium text-sm">How this is calculated</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Cash (income + balance)</span>
                    <span className="font-medium">{fc((readinessData?.income || 0) + (readinessData?.total_balance || 0))}</span>
                  </div>
                  <div className="flex justify-between text-destructive/80">
                    <span>− Elastic Buffer ({elasticBuffer?.buffer_months || 3} months)</span>
                    <span>{fc(readinessData?.effective_buffer || 0)}</span>
                  </div>
                  <div className="flex justify-between text-destructive/80">
                    <span>− Earmarked Bills (fixed + subs)</span>
                    <span>{fc((readinessData?.fixed_costs || 0) + (readinessData?.subscriptions_total || 0))}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Raw Safe to Invest</span>
                    <span className="font-medium">{fc(safeEngine?.raw_safe_to_invest || 0)}</span>
                  </div>
                  <div className="flex justify-between text-amber-600">
                    <span>× 80% confidence (20% shadow buffer)</span>
                    <span>−{fc(safeEngine?.shadow_buffer_amount || 0)}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between font-semibold">
                    <span>Displayed Amount</span>
                    <span>{fc(readinessData?.safe_to_invest || 0)}</span>
                  </div>
                </div>
                {safeEngine?.frozen && (
                  <div className="p-2 bg-blue-50 rounded text-xs text-blue-700 mt-2">
                    {safeEngine.frozen_reason}
                  </div>
                )}
                <div className="pt-2 text-xs text-muted-foreground">
                  <p><strong>Why 80%?</strong> A 20% shadow buffer protects against hidden fees, price slippage, and unexpected charges.</p>
                  {spikeInfo?.spike_detected && <p className="mt-1"><strong>Spike:</strong> Recent spend {fc(spikeInfo.recent_spend)} vs avg {fc(spikeInfo.avg_prior_spend)} ({spikeInfo.spike_pct}% increase)</p>}
                </div>
              </div>
            </PopoverContent>
          </Popover>
        </CardContent>
      </Card>

      <Card className="card-hover" data-testid="svi-card">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">Volatility Index</CardTitle>
          <Activity className={cn("w-5 h-5", svi > 0.35 ? "text-destructive" : "text-accent")} />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-semibold font-heading">{svi.toFixed(2)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {sviData?.months_analyzed || 0} months analyzed
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export function InvestmentReadinessCard({ readinessData, fc, t }) {
  const sviData = readinessData?.svi;
  const elastic = readinessData?.elastic_buffer;
  const spike = readinessData?.spike_detection;
  const safeEngine = readinessData?.safe_to_invest_engine;

  return (
    <Card data-testid="investment-readiness-card">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading">{t('investment_readiness')}</CardTitle>
            <CardDescription>Risk-adjusted analysis powered by your spending patterns</CardDescription>
          </div>
          <Link to="/dashboard/investments">
            <Button variant="outline" size="sm" className="btn-lift">View Options <ArrowRight className="w-4 h-4 ml-2" /></Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* SVI Gauge */}
        {sviData && <SviGauge svi={sviData.svi || 0} />}

        {/* Key Metrics Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center">
              <Shield className="w-6 h-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Elastic Buffer</p>
              <p className="font-semibold" data-testid="elastic-buffer-amount">{fc(readinessData?.effective_buffer || 0)}</p>
              {elastic && (
                <p className="text-[11px] text-muted-foreground">{elastic.buffer_months} months (base {elastic.base_months} + {elastic.svi_adjustment} SVI)</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-primary" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Monthly Income</p>
              <p className="font-semibold">{fc(readinessData?.income || 0)}</p>
              {readinessData?.income_breakdown && (
                <p className="text-[11px] text-muted-foreground">
                  {readinessData.income_breakdown.auto_detected > 0 && `Auto ${fc(readinessData.income_breakdown.auto_detected)}`}
                  {readinessData.income_breakdown.primary_income > 0 && ` + Primary ${fc(readinessData.income_breakdown.primary_income)}`}
                </p>
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">Confidence</span>
              <span className="text-sm font-medium">{Math.round((readinessData?.confidence_level || 0) * 100)}%</span>
            </div>
            <Progress value={(readinessData?.confidence_level || 0) * 100} className="h-2" />
          </div>
        </div>

        {/* Spike Warning */}
        {spike?.spike_detected && (
          <div className={cn("p-4 rounded-lg flex items-start gap-3",
            spike.cooling_off ? "bg-blue-50 border border-blue-200" : "bg-amber-50 border border-amber-200"
          )} data-testid="spike-warning">
            {spike.cooling_off ? <Snowflake className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" /> : <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />}
            <div className="text-sm">
              <p className={cn("font-medium", spike.cooling_off ? "text-blue-800" : "text-amber-800")}>
                {spike.cooling_off ? 'Investment Freeze Active' : 'Spending Spike Detected'}
              </p>
              <p className={cn("mt-1", spike.cooling_off ? "text-blue-700" : "text-amber-700")}>
                Recent spending is {spike.spike_pct}% above your average ({fc(spike.recent_spend)} vs {fc(spike.avg_prior_spend)}).
                {spike.cooling_off && ` Safe to Invest is frozen for a ${14}-day cooling-off period to ensure this isn't a new trend.`}
              </p>
            </div>
          </div>
        )}

        {/* Shadow Buffer Explanation */}
        {safeEngine && !safeEngine.frozen && safeEngine.raw_safe_to_invest > 0 && (
          <div className="p-3 bg-muted/50 rounded-lg text-sm text-muted-foreground flex items-start gap-2" data-testid="shadow-buffer-info">
            <Eye className="w-4 h-4 mt-0.5 flex-shrink-0" />
            <p>Showing {Math.round(safeEngine.shadow_buffer_pct * 100)}% of your investable amount ({fc(safeEngine.raw_safe_to_invest)}). A {fc(safeEngine.shadow_buffer_amount)} shadow buffer is held back for hidden fees and price slippage.</p>
          </div>
        )}

        {/* Risk Disclaimer */}
        <Separator />
        <div className="disclaimer-banner p-4 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-amber-800">Investment Risk Disclaimer</p>
              <p className="text-amber-700 mt-1">All investments carry risk. This analysis is for educational purposes only. Always consult a licensed financial advisor before making investment decisions.</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
