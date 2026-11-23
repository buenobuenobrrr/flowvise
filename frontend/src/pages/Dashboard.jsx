import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Skeleton } from '../components/ui/skeleton';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';
import { Sparkles } from 'lucide-react';
import { getStatusColor } from '../lib/utils';
import { useCurrency } from '../contexts/CurrencyContext';
import { Link } from 'react-router-dom';
import { StatsCards, InvestmentReadinessCard } from '../components/DashboardCards';
import {
  CHART_AXIS_TICK, CHART_TOOLTIP_STYLE, CHART_TOOLTIP_LABEL_STYLE,
  CHART_TOOLTIP_ITEM_STYLE, CHART_COLORS, CHART_GRID_STROKE, CHART_AXIS_STROKE
} from '../lib/chartTheme';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function Dashboard() {
  const { user, getAuthHeaders } = useAuth();
  const { t } = useLanguage();
  const { fc, symbol } = useCurrency();
  const [loading, setLoading] = useState(true);
  const [spendingData, setSpendingData] = useState(null);
  const [readinessData, setReadinessData] = useState(null);
  const [accounts, setAccounts] = useState([]);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [spendingRes, readinessRes, accountsRes] = await Promise.all([
        fetch(`${API}/analysis/spending-summary`, {
          credentials: 'include',
          headers: getAuthHeaders()
        }),
        fetch(`${API}/analysis/investment-readiness`, {
          credentials: 'include',
          headers: getAuthHeaders()
        }),
        fetch(`${API}/bank-accounts`, {
          credentials: 'include',
          headers: getAuthHeaders()
        })
      ]);

      if (spendingRes.ok) {
        setSpendingData(await spendingRes.json());
      }
      if (readinessRes.ok) {
        setReadinessData(await readinessRes.json());
      }
      if (accountsRes.ok) {
        setAccounts(await accountsRes.json());
      }
    } catch (err) {
      setLoading(false); // Ensure loading stops on error
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => {
    fetchDashboardData();
    const onChange = () => fetchDashboardData();
    window.addEventListener('flowvise:data-changed', onChange);
    window.addEventListener('focus', onChange);
    return () => {
      window.removeEventListener('flowvise:data-changed', onChange);
      window.removeEventListener('focus', onChange);
    };
  }, [fetchDashboardData]);

  // Prepare chart data
  const monthlyChartData = spendingData?.by_month
    ? Object.entries(spendingData.by_month).map(([month, amount]) => ({
        month: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][Number(month.slice(5)) - 1] || month,
        spending: amount
      })).slice(-6)
    : [];

  const categoryChartData = spendingData?.by_category
    ? Object.entries(spendingData.by_category).map(([name, value]) => ({
        name,
        value
      }))
    : [];

  const totalBalance = accounts.reduce((sum, acc) => sum + acc.balance, 0);

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main className="px-5 sm:px-8 lg:px-12 pt-8 lg:pt-10 pb-16">
          <div className="max-w-7xl mx-auto space-y-10">
            <Skeleton className="h-8 w-48" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[1, 2, 3, 4].map(i => (
                <Skeleton key={i} className="h-32 rounded-xl" />
              ))}
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-testid="dashboard">
      <Sidebar />

      <main className="px-5 sm:px-8 lg:px-12 pt-8 lg:pt-10 pb-16">
        <div className="max-w-7xl mx-auto space-y-10">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="page-title">
                {t('welcome_back')}, {user?.name?.split(' ')[0]}
              </h1>
              <p className="text-muted-foreground mt-1">
                {t('financial_overview')}
              </p>
            </div>
            <Link to="/dashboard/advisor">
              <Button className="btn-lift" data-testid="get-advice-btn">
                <Sparkles className="w-4 h-4 mr-2" />
                {t('get_ai_advice')}
              </Button>
            </Link>
          </div>

          {/* Stats Cards */}
          <StatsCards totalBalance={totalBalance} accounts={accounts} spendingData={spendingData}
            readinessData={readinessData} fc={fc} t={t} getStatusColor={getStatusColor} />

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Spending Trend */}
            <Card data-testid="spending-chart-card">
              <CardHeader>
                <CardTitle className="font-heading">{t('spending_trend')}</CardTitle>
                <CardDescription>{t('monthly_spending_over_time')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  {monthlyChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={monthlyChartData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                        <defs>
                          <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.22} />
                            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid vertical={false} stroke={CHART_GRID_STROKE} />
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
                          cursor={{ stroke: CHART_AXIS_STROKE, strokeOpacity: 0.35 }}
                        />
                        <Area
                          type="monotone"
                          dataKey="spending"
                          stroke="hsl(var(--primary))"
                          strokeWidth={1.75}
                          fill="url(#spendFill)"
                          dot={false}
                          activeDot={{ r: 4, strokeWidth: 0, fill: 'hsl(var(--primary))' }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-full flex items-center justify-center text-muted-foreground">
                      <p>No spending data yet. Add transactions to see trends.</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Spending by Category */}
            <Card data-testid="category-chart-card">
              <CardHeader>
                <CardTitle className="font-heading">{t('spending_by_category')}</CardTitle>
                <CardDescription>{t('where_money_goes')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  {categoryChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={categoryChartData}
                          cx="50%"
                          cy="50%"
                          innerRadius={68}
                          outerRadius={96}
                          paddingAngle={1.5}
                          dataKey="value"
                          stroke="hsl(var(--card))"
                          strokeWidth={2}
                        >
                          {categoryChartData.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
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
                      <p>No category data yet. Add transactions to see breakdown.</p>
                    </div>
                  )}
                </div>
                {/* Legend below pie so labels never overflow the chart */}
                {categoryChartData.length > 0 && (
                  <div className="flex flex-wrap gap-x-4 gap-y-2 mt-4 px-2 text-xs">
                    {categoryChartData.slice(0, 8).map((item, idx) => (
                      <div key={item.name} className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }} />
                        <span className="text-muted-foreground truncate max-w-[140px]">{item.name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Investment Readiness */}
          <InvestmentReadinessCard readinessData={readinessData} fc={fc} t={t} />
        </div>
      </main>
    </div>
  );
}
