import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { Slider } from './ui/slider';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from './ui/select';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from './ui/alert-dialog';
import { User, DollarSign, Shield, PiggyBank, Globe, Bell, Download, Trash2, Zap, Loader2, Moon, Sun } from 'lucide-react';
import { toast } from 'sonner';
import { useState, useEffect } from 'react';
import { useTheme } from '../contexts/ThemeContext';

export function ProfileCard({ user, t }) {
  return (
    <Card data-testid="profile-card">
      <CardHeader>
        <div className="flex items-center gap-2"><User className="w-5 h-5 text-primary" /><CardTitle className="font-heading">{t('profile')}</CardTitle></div>
        <CardDescription>{t('account_info')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div><Label className="text-muted-foreground">Name</Label><p className="font-medium">{user?.name}</p></div>
          <div><Label className="text-muted-foreground">Email</Label><p className="font-medium">{user?.email}</p></div>
        </div>
      </CardContent>
    </Card>
  );
}

export function CurrencyCard({ currency, setCurrency, currencies, t }) {
  return (
    <Card data-testid="currency-card">
      <CardHeader>
        <div className="flex items-center gap-2"><Globe className="w-5 h-5 text-primary" /><CardTitle className="font-heading">Currency</CardTitle></div>
        <CardDescription>Auto-detected from your browser. Override if needed.</CardDescription>
      </CardHeader>
      <CardContent>
        <Select value={currency} onValueChange={setCurrency}>
          <SelectTrigger data-testid="currency-select"><SelectValue /></SelectTrigger>
          <SelectContent>
            {currencies.map(c => <SelectItem key={c.code} value={c.code}>{c.flag} {c.code} — {c.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </CardContent>
    </Card>
  );
}

export function IncomeCard({ profile, setProfile, fc, t, getAuthHeaders }) {
  const totalSubs = Object.values(profile.subscriptions).reduce((a, b) => a + b, 0);
  const [incomeData, setIncomeData] = useState(null);
  const [loadingIncome, setLoadingIncome] = useState(true);
  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  useEffect(() => {
    const fetchIncome = async () => {
      try {
        const res = await fetch(`${API}/analysis/income-breakdown`, { credentials: 'include', headers: getAuthHeaders() });
        if (res.ok) setIncomeData(await res.json());
      } catch (err) {
        if (process.env.NODE_ENV !== 'production') console.error('Income fetch failed:', err);
      }
      finally { setLoadingIncome(false); }
    };
    fetchIncome();
  }, [API, getAuthHeaders]);

  const autoIncome = incomeData?.auto_detected?.avg_monthly_income || 0;
  const primaryIncome = profile.primary_income || 0;
  const totalIncome = autoIncome + primaryIncome + (profile.income || 0);

  return (
    <Card data-testid="income-expenses-card">
      <CardHeader>
        <div className="flex items-center gap-2"><DollarSign className="w-5 h-5 text-primary" /><CardTitle className="font-heading">{t('income_fixed')}</CardTitle></div>
        <CardDescription>Auto-detected from bank inflows + your primary income</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Auto-detected income */}
        <div className="p-4 bg-green-50 dark:bg-green-950/30 rounded-lg space-y-2" data-testid="auto-income-section">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-green-700 dark:text-green-400">Auto-detected Monthly Income</span>
            <span className="text-lg font-semibold text-green-700 dark:text-green-400">
              {loadingIncome ? '...' : fc(autoIncome)}
            </span>
          </div>
          {incomeData?.auto_detected?.sources?.length > 0 && (
            <div className="space-y-1 mt-2">
              {incomeData.auto_detected.sources.slice(0, 5).map((src, i) => (
                <div key={`${src.description}-${i}`} className="flex justify-between text-xs text-muted-foreground">
                  <span className="truncate max-w-[200px]">{src.description} {src.recurring && <Badge variant="outline" className="ml-1 text-[9px] py-0">recurring</Badge>}</span>
                  <span>{fc(src.monthly_avg)}/mo</span>
                </div>
              ))}
            </div>
          )}
          {incomeData?.auto_detected?.months_analyzed > 0 && (
            <p className="text-xs text-green-600 dark:text-green-500">Based on {incomeData.auto_detected.months_analyzed} months of bank data</p>
          )}
        </div>

        <Separator />

        {/* Manual inputs */}
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-2">
            <Label htmlFor="primary_income">Primary Income (fixed)</Label>
            <Input id="primary_income" data-testid="primary-income-input" type="number" step="100"
              placeholder="e.g. salary, pension..."
              value={primaryIncome || ''}
              onChange={(e) => setProfile({ ...profile, primary_income: parseFloat(e.target.value) || 0 })} />
            <p className="text-xs text-muted-foreground">Your main stable income source</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="fixed_costs">{t('fixed_costs_label')}</Label>
            <Input id="fixed_costs" data-testid="fixed-costs-input" type="number" step="100" value={profile.fixed_costs}
              onChange={(e) => setProfile({ ...profile, fixed_costs: parseFloat(e.target.value) || 0 })} />
            <p className="text-xs text-muted-foreground">{t('fixed_costs_hint')}</p>
          </div>
        </div>

        <div className="p-4 bg-muted/50 rounded-lg space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Total Monthly Income</span>
            <span className="font-semibold">{fc(totalIncome)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{t('net_monthly')}</span>
            <span className="font-semibold">{fc(totalIncome - profile.fixed_costs - totalSubs)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function SafetyBufferCard({ profile, setProfile, fc, t }) {
  return (
    <Card data-testid="safety-buffer-card">
      <CardHeader>
        <div className="flex items-center gap-2"><Shield className="w-5 h-5 text-primary" /><CardTitle className="font-heading">{t('safety_buffer_title')}</CardTitle></div>
        <CardDescription>{t('emergency_fund')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex justify-between"><Label>{t('buffer_amount')}</Label><span className="font-semibold">{fc(profile.safety_buffer)}</span></div>
        <Slider value={[profile.safety_buffer]} onValueChange={([v]) => setProfile({ ...profile, safety_buffer: v })} max={10000} step={100} data-testid="safety-buffer-slider" />
        <div className="flex justify-between text-xs text-muted-foreground"><span>{fc(0)}</span><span>{fc(10000)}</span></div>
      </CardContent>
    </Card>
  );
}

export function RiskToleranceCard({ profile, setProfile, t }) {
  return (
    <Card data-testid="risk-tolerance-card">
      <CardHeader>
        <div className="flex items-center gap-2"><PiggyBank className="w-5 h-5 text-primary" /><CardTitle className="font-heading">{t('risk_tolerance_title')}</CardTitle></div>
        <CardDescription>{t('risk_preference')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Select value={profile.risk_tolerance} onValueChange={(v) => setProfile({ ...profile, risk_tolerance: v })}>
          <SelectTrigger data-testid="risk-tolerance-select"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="conservative">{t('conservative_desc')}</SelectItem>
            <SelectItem value="moderate">{t('moderate_desc')}</SelectItem>
            <SelectItem value="aggressive">{t('aggressive_desc')}</SelectItem>
          </SelectContent>
        </Select>
      </CardContent>
    </Card>
  );
}

export function SubscriptionsCard({ profile, setProfile, fc, t }) {
  const totalSubs = Object.values(profile.subscriptions).reduce((a, b) => a + b, 0);
  const [newSub, setNewSub] = [profile._newSub || { name: '', amount: '' }, (v) => setProfile({ ...profile, _newSub: v })];

  const handleAdd = () => {
    if (!newSub.name || !newSub.amount) { toast.error('Please fill in subscription details'); return; }
    setProfile({
      ...profile,
      subscriptions: { ...profile.subscriptions, [newSub.name]: parseFloat(newSub.amount) },
      _newSub: { name: '', amount: '' }
    });
  };

  const handleRemove = (name) => {
    const { [name]: _, ...rest } = profile.subscriptions;
    setProfile({ ...profile, subscriptions: rest });
  };

  return (
    <Card data-testid="subscriptions-card">
      <CardHeader>
        <CardTitle className="font-heading">{t('subscriptions_title')}</CardTitle>
        <CardDescription>{t('track_recurring')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-2">
          <Input placeholder={t('subscription_name')} value={newSub.name}
            onChange={(e) => setNewSub({ ...newSub, name: e.target.value })} data-testid="subscription-name-input" />
          <Input type="number" placeholder="Amount" className="w-32" value={newSub.amount}
            onChange={(e) => setNewSub({ ...newSub, amount: e.target.value })} data-testid="subscription-amount-input" />
          <Button onClick={handleAdd} data-testid="add-subscription-button">Add</Button>
        </div>
        {Object.keys(profile.subscriptions).length > 0 ? (
          <div className="space-y-2">
            {Object.entries(profile.subscriptions).map(([name, amount]) => (
              <div key={name} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg" data-testid={`subscription-${name}`}>
                <span>{name}</span>
                <div className="flex items-center gap-3">
                  <span className="font-medium">{fc(amount)}/mo</span>
                  <Button variant="ghost" size="sm" onClick={() => handleRemove(name)} className="text-muted-foreground hover:text-destructive">Remove</Button>
                </div>
              </div>
            ))}
            <Separator />
            <div className="flex justify-between font-medium"><span>{t('total_subscriptions')}</span><span>{fc(totalSubs)}/mo</span></div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-4">{t('no_subscriptions')}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function NotificationsCard({ notifSupported, notifEnabled, requestPermission, t }) {
  if (!notifSupported) return null;
  return (
    <Card data-testid="notifications-card">
      <CardHeader>
        <div className="flex items-center gap-2"><Bell className="w-5 h-5 text-primary" /><CardTitle className="font-heading">{t('notifications_title')}</CardTitle></div>
        <CardDescription>{t('notifications_subtitle')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
          <div>
            <p className="font-medium text-sm">{t('enable_push')}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{t('push_desc')}</p>
          </div>
          {notifEnabled ? (
            <Badge className="bg-green-100 text-green-700">{t('notifications_enabled')}</Badge>
          ) : (
            <Button size="sm" onClick={async () => { const r = await requestPermission(); if (r === 'granted') toast.success(t('notifications_enabled')); }}
              data-testid="enable-notifications-button">{t('enable_notifications')}</Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function AutoDetectCard({ getAuthHeaders, fc, onApplied }) {
  const [loading, setLoading] = useState(false);
  const [detected, setDetected] = useState(null);
  const [applying, setApplying] = useState(false);
  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  const handleDetect = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/analysis/auto-detect`, { credentials: 'include', headers: getAuthHeaders() });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setDetected(data);
      if (!data.detected_income.length && !data.detected_subscriptions.length) {
        toast.info('No recurring patterns found. Add more transactions first.');
      }
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Auto-detect error:', err);
      toast.error('Failed to detect patterns');
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    if (!detected) return;
    setApplying(true);
    try {
      const payload = {};
      if (detected.estimated_monthly_income > 0) payload.income = detected.estimated_monthly_income;
      if (Object.keys(detected.suggested_subscriptions_map).length > 0) payload.subscriptions = detected.suggested_subscriptions_map;
      if (detected.estimated_monthly_subscriptions > 0) payload.fixed_costs = detected.estimated_monthly_subscriptions;

      const res = await fetch(`${API}/analysis/auto-detect/apply`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error();
      toast.success('Auto-detected values applied to your profile!');
      if (onApplied) onApplied();
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Apply detected values error:', err);
      toast.error('Failed to apply detected values');
    } finally {
      setApplying(false);
    }
  };

  return (
    <Card data-testid="auto-detect-card">
      <CardHeader>
        <div className="flex items-center gap-2"><Zap className="w-5 h-5 text-primary" /><CardTitle className="font-heading">Smart Detection</CardTitle></div>
        <CardDescription>Automatically detect recurring income and subscriptions from your transactions.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={handleDetect} disabled={loading} variant="outline" className="w-full" data-testid="auto-detect-button">
          {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Zap className="w-4 h-4 mr-2" />}
          {loading ? 'Scanning transactions...' : 'Scan Transactions'}
        </Button>

        {detected && (
          <div className="space-y-3">
            {detected.detected_income.length > 0 && (
              <div className="p-3 bg-green-50 dark:bg-green-950/30 rounded-lg">
                <p className="text-sm font-medium text-green-700 dark:text-green-400 mb-2">Detected Income</p>
                {detected.detected_income.map((inc, i) => (
                  <div key={`${inc.description}-${inc.average_amount}`} className="flex justify-between text-sm" data-testid={`detected-income-${i}`}>
                    <span>{inc.description || inc.category}</span>
                    <span className="font-medium">{fc(inc.average_amount)}/{inc.frequency === 'weekly' ? 'wk' : 'mo'}</span>
                  </div>
                ))}
                <Separator className="my-2" />
                <div className="flex justify-between text-sm font-medium">
                  <span>Est. Monthly Income</span>
                  <span>{fc(detected.estimated_monthly_income)}</span>
                </div>
              </div>
            )}

            {detected.detected_subscriptions.length > 0 && (
              <div className="p-3 bg-orange-50 dark:bg-orange-950/30 rounded-lg">
                <p className="text-sm font-medium text-orange-700 dark:text-orange-400 mb-2">Detected Subscriptions</p>
                {detected.detected_subscriptions.slice(0, 8).map((sub, i) => (
                  <div key={`${sub.description}-${sub.average_amount}`} className="flex justify-between text-sm" data-testid={`detected-sub-${i}`}>
                    <span>{sub.description || sub.category}</span>
                    <span className="font-medium">{fc(sub.average_amount)}/{sub.frequency === 'weekly' ? 'wk' : 'mo'}</span>
                  </div>
                ))}
                <Separator className="my-2" />
                <div className="flex justify-between text-sm font-medium">
                  <span>Est. Monthly Subscriptions</span>
                  <span>{fc(detected.estimated_monthly_subscriptions)}</span>
                </div>
              </div>
            )}

            {(detected.detected_income.length > 0 || detected.detected_subscriptions.length > 0) && (
              <Button onClick={handleApply} disabled={applying} className="w-full" data-testid="apply-detected-button">
                {applying ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                Apply to My Profile
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function ThemeCard() {
  const { theme, setTheme } = useTheme();
  return (
    <Card data-testid="theme-card">
      <CardHeader>
        <div className="flex items-center gap-2">
          {theme === 'dark' ? <Moon className="w-5 h-5 text-primary" /> : <Sun className="w-5 h-5 text-primary" />}
          <CardTitle className="font-heading">Appearance</CardTitle>
        </div>
        <CardDescription>Choose your preferred theme</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3">
          {[
            { value: 'dark', label: 'Dark', icon: Moon },
            { value: 'light', label: 'Light', icon: Sun },
            { value: 'system', label: 'System', icon: Globe },
          ].map(({ value, label, icon: Icon }) => (
            <button key={value} onClick={() => {
              if (value === 'system') {
                const sys = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                setTheme(sys);
              } else {
                setTheme(value);
              }
            }}
              className={`flex flex-col items-center gap-2 p-4 rounded-lg border transition-all ${
                theme === value ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/30'
              }`}
              data-testid={`theme-${value}`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-sm font-medium">{label}</span>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function GdprCard({ getAuthHeaders, onAccountDeleted }) {
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API}/user/export`, { credentials: 'include', headers: getAuthHeaders() });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `flowvise-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Data exported successfully');
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Export error:', err);
      toast.error('Failed to export data');
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      const res = await fetch(`${API}/user/account`, {
        method: 'DELETE', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({ confirm: 'DELETE' })
      });
      if (!res.ok) throw new Error();
      toast.success('Account deleted permanently');
      if (onAccountDeleted) onAccountDeleted();
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Delete account error:', err);
      toast.error('Failed to delete account');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Card data-testid="gdpr-card" className="border-destructive/30">
      <CardHeader>
        <div className="flex items-center gap-2"><Shield className="w-5 h-5 text-destructive" /><CardTitle className="font-heading">Privacy & Data</CardTitle></div>
        <CardDescription>GDPR: Export or permanently delete your data.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
          <div>
            <p className="font-medium text-sm">Export All Data</p>
            <p className="text-xs text-muted-foreground mt-0.5">Download a JSON file with all your FlowVise data.</p>
          </div>
          <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting} data-testid="export-data-button">
            {exporting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" />}
            Export
          </Button>
        </div>

        <div className="flex items-center justify-between p-4 bg-destructive/5 rounded-lg border border-destructive/20">
          <div>
            <p className="font-medium text-sm text-destructive">Delete Account</p>
            <p className="text-xs text-muted-foreground mt-0.5">Permanently delete your account and all data. This cannot be undone.</p>
          </div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm" data-testid="delete-account-trigger">
                <Trash2 className="w-4 h-4 mr-2" />Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This will permanently delete your account, financial profile, transactions, budgets, and all other data. This action cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel data-testid="delete-account-cancel">Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleDelete} disabled={deleting}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  data-testid="delete-account-confirm">
                  {deleting ? 'Deleting...' : 'Yes, delete everything'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
