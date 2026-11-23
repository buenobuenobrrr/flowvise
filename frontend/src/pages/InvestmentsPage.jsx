import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Progress } from '../components/ui/progress';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import { AlertTriangle, Shield, TrendingUp, DollarSign } from 'lucide-react';
import { formatCurrency, getRiskColor, cn } from '../lib/utils';
import { toast } from 'sonner';
import { InvestmentPortfolioTabs, BankSafeOptions } from '../components/InvestmentComponents';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function InvestmentsPage() {
  const { getAuthHeaders } = useAuth();
  const { fc } = useCurrency();
  const [readiness, setReadiness] = useState(null);
  const [investmentOptions, setInvestmentOptions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [readinessRes, optionsRes] = await Promise.all([
        fetch(`${API}/analysis/investment-readiness`, { credentials: 'include', headers: getAuthHeaders() }),
        fetch(`${API}/investments/options`, { credentials: 'include', headers: getAuthHeaders() })
      ]);
      if (readinessRes.ok) setReadiness(await readinessRes.json());
      if (optionsRes.ok) setInvestmentOptions(await optionsRes.json());
    } catch (err) {
      setLoading(false);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleAcceptDisclaimer = () => {
    setDisclaimerAccepted(true);
    setShowDisclaimer(false);
    toast.success('You can now view investment options');
  };

  const getStatusBadge = (status) => {
    const cfg = { excellent: 'bg-green-100 text-green-700', good: 'bg-emerald-100 text-emerald-700', moderate: 'bg-amber-100 text-amber-700', not_recommended: 'bg-red-100 text-red-700' };
    const label = { excellent: 'Excellent', good: 'Good', moderate: 'Moderate', not_recommended: 'Not Recommended' };
    return <Badge className={cfg[status] || cfg.moderate}>{label[status] || 'Moderate'}</Badge>;
  };

  if (loading) return (
    <div className="min-h-screen bg-background"><Sidebar /><main className="lg:ml-60 pt-16 lg:pt-0 p-6"><div className="max-w-6xl mx-auto animate-pulse space-y-6"><div className="h-8 w-64 bg-muted rounded" /><div className="h-48 bg-muted rounded-lg" /></div></main></div>
  );

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />

      {/* Risk Disclaimer */}
      <Dialog open={showDisclaimer && !disclaimerAccepted} onOpenChange={setShowDisclaimer}>
        <DialogContent className="sm:max-w-lg" data-testid="risk-disclaimer-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-amber-500" />Investment Risk Disclaimer</DialogTitle>
            <DialogDescription>Please read and acknowledge before proceeding</DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg space-y-3 text-sm">
              <p className="font-medium text-amber-800">Important Notice:</p>
              <ul className="space-y-2 text-amber-700">
                {['All investments carry risk. You may lose some or all of your capital.',
                  'Past performance does not guarantee future results.',
                  'We are NOT brokers. This information is educational only.',
                  'Investing according to any recommendation is entirely at your own risk.',
                  'Always consult a licensed financial advisor for major decisions.'].map(text => (
                  <li key={text.slice(0, 20)} className="flex items-start gap-2"><AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" /><span>{text}</span></li>
                ))}
              </ul>
            </div>
            <p className="text-sm text-muted-foreground">By clicking "I Understand", you acknowledge the risks involved.</p>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => window.history.back()}>Go Back</Button>
            <Button onClick={handleAcceptDisclaimer} data-testid="accept-disclaimer-button">I Understand the Risks</Button>
          </div>
        </DialogContent>
      </Dialog>

      <main className="lg:ml-60 pt-16 lg:pt-0 p-6" data-testid="investments-page">
        <div className="max-w-6xl mx-auto space-y-6">
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-semibold tracking-tight">Investment Options</h1>
            <p className="text-muted-foreground mt-1">Explore European investment opportunities</p>
          </div>

          {/* Readiness Summary */}
          <Card data-testid="investment-readiness-summary">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div><CardTitle className="font-heading">Your Investment Readiness</CardTitle><CardDescription>Based on your financial profile</CardDescription></div>
                {getStatusBadge(readiness?.status)}
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div><p className="text-sm text-muted-foreground mb-1">Safe to Invest</p><p className="text-2xl font-semibold font-heading">{fc(readiness?.safe_to_invest || 0)}</p></div>
                <div><p className="text-sm text-muted-foreground mb-1">Confidence Level</p><div className="flex items-center gap-3"><Progress value={(readiness?.confidence_level || 0) * 100} className="flex-1" /><span className="font-medium">{Math.round((readiness?.confidence_level || 0) * 100)}%</span></div></div>
                <div><p className="text-sm text-muted-foreground mb-1">Risk Tolerance</p><Badge className={getRiskColor(readiness?.risk_tolerance)} variant="secondary">{readiness?.risk_tolerance || 'Moderate'}</Badge></div>
                <div><p className="text-sm text-muted-foreground mb-1">Volatility Ratio</p><p className="text-lg font-medium">{readiness?.volatility_ratio || 0}</p></div>
              </div>
            </CardContent>
          </Card>

          {/* Portfolio Tabs */}
          {disclaimerAccepted && investmentOptions && <InvestmentPortfolioTabs investmentOptions={investmentOptions} fc={fc} />}

          {/* Bank Safe Options */}
          {disclaimerAccepted && <BankSafeOptions options={investmentOptions?.bank_safe_options} fc={fc} />}

          {/* CFD Warning */}
          {disclaimerAccepted && investmentOptions?.cfd_warning && (
            <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                <div className="text-sm"><p className="font-medium text-red-800">CFD Risk Warning</p><p className="text-red-700 mt-1">{investmentOptions.cfd_warning}</p></div>
              </div>
            </div>
          )}

          {/* Disclaimer Banner */}
          <div className="disclaimer-banner p-4 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm"><p className="font-medium text-amber-800">Reminder: We Are Not Brokers</p>
                <p className="text-amber-700 mt-1">{investmentOptions?.disclaimer || 'All investments carry risk.'}</p></div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
