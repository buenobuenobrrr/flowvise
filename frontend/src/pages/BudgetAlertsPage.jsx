import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger, DialogFooter
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import {
  Bell, Plus, Trash2, AlertTriangle, CheckCircle, TrendingUp, RefreshCw, Loader2, Zap
} from 'lucide-react';
import { formatCurrency, cn } from '../lib/utils';
import { useCurrency } from '../contexts/CurrencyContext';
import { toast } from 'sonner';
import { useLanguage } from '../contexts/LanguageContext';
import { useNotifications } from '../hooks/useNotifications';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DEFAULT_CATEGORIES = [
  'Food & Dining', 'Shopping', 'Transportation', 'Entertainment',
  'Bills & Utilities', 'Healthcare', 'Personal Care', 'Education', 'Travel', 'Other'
];

function StatusIcon({ status }) {
  switch (status) {
    case 'exceeded':
      return <AlertTriangle className="w-5 h-5 text-red-500" />;
    case 'warning':
      return <AlertTriangle className="w-5 h-5 text-amber-500" />;
    case 'caution':
      return <TrendingUp className="w-5 h-5 text-amber-400" />;
    default:
      return <CheckCircle className="w-5 h-5 text-green-500" />;
  }
}

export default function BudgetAlertsPage() {
  const { getAuthHeaders } = useAuth();
  const { t } = useLanguage();
  const { fc } = useCurrency();
  const { checkBudgetAlerts, isEnabled: notificationsEnabled } = useNotifications();
  const [budgets, setBudgets] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [smartAlerts, setSmartAlerts] = useState([]);
  const [recurring, setRecurring] = useState([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [newBudget, setNewBudget] = useState({ category: '', limit: '', period: 'monthly' });
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API}/categories`, { credentials: 'include', headers: getAuthHeaders() });
      if (res.ok) { const data = await res.json(); setCategories(data.all || DEFAULT_CATEGORIES); }
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Categories fetch failed:', err);
    }
  }, [getAuthHeaders]);

  const fetchAll = useCallback(async () => {
    try {
      const headers = getAuthHeaders();
      const opts = { credentials: 'include', headers };
      const [budRes, alertRes, smartRes, recurRes] = await Promise.all([
        fetch(`${API}/budgets`, opts),
        fetch(`${API}/budgets/alerts`, opts),
        fetch(`${API}/budgets/smart-alerts`, opts),
        fetch(`${API}/transactions/recurring`, opts)
      ]);
      if (budRes.ok) setBudgets(await budRes.json());
      if (alertRes.ok) { const d = await alertRes.json(); setAlerts(d.alerts || []); if (notificationsEnabled) checkBudgetAlerts(d.alerts || []); }
      if (smartRes.ok) { const d = await smartRes.json(); setSmartAlerts(d.alerts || []); }
      if (recurRes.ok) { const d = await recurRes.json(); setRecurring(d.recurring || []); }
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Budget data load failed:', err);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders, notificationsEnabled, checkBudgetAlerts]);

  useEffect(() => { fetchAll(); fetchCategories(); }, [fetchAll, fetchCategories]);

  const handleAddBudget = async () => {
    if (!newBudget.category || !newBudget.limit) { toast.error('Fill in all fields'); return; }
    try {
      const res = await fetch(`${API}/budgets`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({ ...newBudget, limit: parseFloat(newBudget.limit) })
      });
      if (!res.ok) throw new Error();
      toast.success('Budget created');
      setAddOpen(false);
      setNewBudget({ category: '', limit: '', period: 'monthly' });
      await fetchAll();
    } catch (err) { toast.error('Failed to create budget'); }
  };

  const handleDeleteBudget = async (id) => {
    try {
      await fetch(`${API}/budgets/${id}`, { method: 'DELETE', credentials: 'include', headers: getAuthHeaders() });
      toast.success('Budget deleted');
      await fetchAll();
    } catch (err) { toast.error('Failed to delete'); }
  };

  const handleConfirmRecurring = async (item) => {
    try {
      await fetch(`${API}/transactions/recurring/confirm`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({ description: item.description, category: item.category, amount: item.average_amount, frequency: item.frequency })
      });
      toast.success(`Confirmed "${item.description}" as recurring`);
      await fetchAll();
    } catch (err) { toast.error('Failed to confirm'); }
  };

  const handleDismissRecurring = async (id) => {
    if (!id) return;
    try {
      await fetch(`${API}/transactions/recurring/${id}`, { method: 'DELETE', credentials: 'include', headers: getAuthHeaders() });
      toast.success('Dismissed');
      await fetchAll();
    } catch (err) { toast.error('Failed to dismiss'); }
  };

  const getProgressColor = (status) => {
    switch (status) {
      case 'exceeded': return '[&>div]:bg-red-500';
      case 'warning': return '[&>div]:bg-amber-500';
      case 'caution': return '[&>div]:bg-amber-300';
      default: return '[&>div]:bg-green-500';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="lg:ml-60 pt-16 lg:pt-0 p-6" data-testid="budget-alerts-page">
        <div className="max-w-6xl mx-auto space-y-6">

          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="font-heading text-2xl sm:text-3xl font-semibold tracking-tight">
                {t('budget_alerts_title')}
              </h1>
              <p className="text-muted-foreground mt-1">
                {t('budget_alerts_subtitle')}
              </p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={fetchAll} data-testid="refresh-alerts">
                <RefreshCw className="w-4 h-4 mr-1" /> Refresh
              </Button>
              <Dialog open={addOpen} onOpenChange={setAddOpen}>
                <DialogTrigger asChild>
                  <Button className="btn-lift" data-testid="add-budget-button">
                    <Plus className="w-4 h-4 mr-2" /> Add Budget
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle className="font-heading">Create Budget</DialogTitle>
                    <DialogDescription>Set a spending limit for a category</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Category</Label>
                      <Select value={newBudget.category} onValueChange={(v) => setNewBudget({ ...newBudget, category: v })}>
                        <SelectTrigger data-testid="budget-category-select"><SelectValue placeholder="Select..." /></SelectTrigger>
                        <SelectContent>
                          {categories.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Monthly Limit (EUR)</Label>
                      <Input data-testid="budget-limit-input" type="number" step="10" placeholder="500" value={newBudget.limit} onChange={(e) => setNewBudget({ ...newBudget, limit: e.target.value })} />
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
                    <Button onClick={handleAddBudget} data-testid="confirm-add-budget">Create</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </div>

          {/* Budget Alerts */}
          <Card data-testid="budget-alerts-card">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bell className="w-5 h-5 text-primary" />
                <CardTitle className="font-heading">Spending vs Budget</CardTitle>
              </div>
              <CardDescription>How your spending compares to your limits this month</CardDescription>
            </CardHeader>
            <CardContent>
              {alerts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Bell className="w-10 h-10 mx-auto mb-3 opacity-40" />
                  <p>No budgets set yet. Create one to start tracking.</p>
                </div>
              ) : (
                <div className="space-y-5">
                  {alerts.map((a) => (
                    <div key={a.budget_id} className="space-y-2" data-testid={`alert-${a.category.replace(/\s/g,'-')}`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <StatusIcon status={a.status} />
                          <span className="font-medium">{a.category}</span>
                          <Badge variant="outline" className={cn(
                            a.status === 'exceeded' && 'border-red-300 text-red-600',
                            a.status === 'warning' && 'border-amber-300 text-amber-600',
                            a.status === 'safe' && 'border-green-300 text-green-600'
                          )}>
                            {a.status}
                          </Badge>
                        </div>
                        <div className="text-right">
                          <span className="font-medium">{fc(a.spent)}</span>
                          <span className="text-muted-foreground"> / {fc(a.limit)}</span>
                        </div>
                      </div>
                      <Progress value={Math.min(a.percentage, 100)} className={cn("h-2.5", getProgressColor(a.status))} />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{a.percentage}% used</span>
                        <span>{fc(a.remaining)} remaining</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Budget list with delete */}
              {budgets.length > 0 && (
                <div className="mt-6 pt-4 border-t space-y-2">
                  <p className="text-sm text-muted-foreground font-medium">Your budgets:</p>
                  {budgets.map(b => (
                    <div key={b.budget_id} className="flex items-center justify-between py-2">
                      <span className="text-sm">{b.category}: {fc(b.limit)}/mo</span>
                      <Button variant="ghost" size="sm" onClick={() => handleDeleteBudget(b.budget_id)} className="text-muted-foreground hover:text-destructive">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Smart Alerts */}
          <Card data-testid="smart-alerts-card">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-500" />
                <CardTitle className="font-heading">Smart Alerts</CardTitle>
              </div>
              <CardDescription>AI-detected spending patterns and anomalies</CardDescription>
            </CardHeader>
            <CardContent>
              {smartAlerts.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <p>No anomalies detected. Keep spending wisely!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {smartAlerts.map((a, i) => (
                    <div key={`${a.type}-${a.category || a.description || i}`} className={cn(
                      "p-4 rounded-lg border-l-4",
                      a.type === 'spending_spike' ? 'border-l-amber-500 bg-amber-50' : 'border-l-red-500 bg-red-50'
                    )} data-testid={`smart-alert-${i}`}>
                      <div className="flex items-start gap-3">
                        {a.type === 'spending_spike' ? (
                          <TrendingUp className="w-5 h-5 text-amber-600 mt-0.5" />
                        ) : (
                          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5" />
                        )}
                        <div>
                          <p className="font-medium text-sm">{a.message}</p>
                          {a.type === 'spending_spike' && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Previous: {fc(a.previous_amount)} → Current: {fc(a.current_amount)} (+{a.increase_pct}%)
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recurring Transactions */}
          <Card data-testid="recurring-transactions-card">
            <CardHeader>
              <div className="flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-primary" />
                <CardTitle className="font-heading">Detected Recurring Transactions</CardTitle>
              </div>
              <CardDescription>
                Auto-detected patterns — confirm to track as subscriptions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {recurring.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <RefreshCw className="w-10 h-10 mx-auto mb-3 opacity-40" />
                  <p>No recurring patterns detected yet. Add more transactions for detection.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {recurring.map((r, i) => (
                    <div key={r.pattern_id || `${r.description}-${r.average_amount}`} className="flex items-center justify-between p-4 border rounded-lg" data-testid={`recurring-${i}`}>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{r.description}</p>
                          <Badge variant="secondary">{r.category}</Badge>
                          <Badge variant="outline" className="capitalize">{r.frequency}</Badge>
                          {r.confirmed && <Badge className="bg-green-100 text-green-700">Confirmed</Badge>}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {fc(r.average_amount)} · {r.occurrences} occurrences · Every ~{r.avg_interval_days} days
                        </p>
                      </div>
                      <div className="flex gap-2">
                        {!r.confirmed ? (
                          <Button size="sm" onClick={() => handleConfirmRecurring(r)} data-testid={`confirm-recurring-${i}`}>
                            Confirm
                          </Button>
                        ) : (
                          <Button size="sm" variant="ghost" onClick={() => handleDismissRecurring(r.confirmed_id)} className="text-muted-foreground hover:text-destructive">
                            Remove
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      </main>
    </div>
  );
}
