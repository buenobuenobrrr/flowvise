import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger,
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '../components/ui/table';
import { Building, Plus, Unlink, CreditCard, Landmark, Loader2, CheckCircle, ExternalLink, RefreshCw } from 'lucide-react';
import { useCurrency } from '../contexts/CurrencyContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const MOCK_INSTITUTIONS = [
  { id: 'ing', name: 'ING Bank', logo: '\u{1F3E6}' },
  { id: 'bnp', name: 'BNP Paribas', logo: '\u{1F3DB}' },
  { id: 'deutsche', name: 'Deutsche Bank', logo: '\u{1F3E6}' },
  { id: 'santander', name: 'Santander', logo: '\u{1F3DB}' },
  { id: 'n26', name: 'N26', logo: '\u{1F3E6}' },
  { id: 'revolut', name: 'Revolut', logo: '\u{1F3E6}' },
  { id: 'rabobank', name: 'Rabobank', logo: '\u{1F3DB}' },
  { id: 'abnamro', name: 'ABN AMRO', logo: '\u{1F3E6}' },
];

export default function BankAccountsPage() {
  const { getAuthHeaders } = useAuth();
  const { fc } = useCurrency();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [linkDialogOpen, setLinkDialogOpen] = useState(false);
  const [linkMode, setLinkMode] = useState(null); // 'tink' | 'demo'
  const [selectedInstitution, setSelectedInstitution] = useState('');
  const [linkStep, setLinkStep] = useState('choose'); // choose, connecting, success
  const [tinkLinkUrl, setTinkLinkUrl] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await fetch(`${API}/bank-accounts`, { credentials: 'include', headers: getAuthHeaders() });
      if (res.ok) setAccounts(await res.json());
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Accounts fetch failed:', err);
      toast.error('Failed to load accounts');
    }
    finally { setLoading(false); }
  }, [getAuthHeaders]);

  useEffect(() => { fetchAccounts(); }, [fetchAccounts]);

  // Stable ref to handleTinkCallback so the URL-param mount effect can fire it
  // without re-running every render (the callback closes over many state setters).
  const tinkCallbackRef = useRef(null);

  // Check for Tink callback on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const credentialsId = params.get('credentials_id');
    const error = params.get('error');
    if (error) {
      toast.error(`Bank connection failed: ${params.get('message') || error}`);
      window.history.replaceState({}, '', window.location.pathname);
      return;
    }
    if (code) {
      window.history.replaceState({}, '', window.location.pathname);
      tinkCallbackRef.current?.(code, credentialsId);
    }
  }, []);

  const handleTinkCallback = async (code, credentialsId) => {
    setLinkDialogOpen(true);
    setLinkStep('connecting');
    setLinking(true);
    try {
      const res = await fetch(`${API}/tink/callback`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({ code, credentials_id: credentialsId })
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) { /* non-json */ }
      if (!res.ok) {
        throw new Error(data.detail || `Failed to process bank connection (HTTP ${res.status})`);
      }
      setLinkStep('success');
      await new Promise(r => setTimeout(r, 1500));
      await fetchAccounts();
      toast.success(data.message || 'Bank connected!');
    } catch (err) {
      toast.error(err.message || 'Failed to connect bank');
      setLinkStep('choose');
    } finally {
      setLinking(false);
      setLinkDialogOpen(false);
      setLinkStep('choose');
    }
  };
  // Keep ref in sync so the mount-only effect can invoke the latest closure.
  tinkCallbackRef.current = handleTinkCallback;

  const handleTinkLink = async () => {
    setLinking(true);
    setLinkStep('connecting');
    try {
      const redirectUri = `${window.location.origin}/dashboard/accounts`;
      const res = await fetch(`${API}/tink/link`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({ redirect_uri: redirectUri })
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) { /* non-json response */ }
      if (!res.ok) {
        throw new Error(data.detail || `Failed to create Tink link (HTTP ${res.status})`);
      }
      setTinkLinkUrl(data.url);
      setLinkStep('redirect');
    } catch (err) {
      toast.error(err.message || 'Failed to start bank connection');
      setLinkStep('choose');
    } finally {
      setLinking(false);
    }
  };

  const handleDemoLink = async () => {
    if (!selectedInstitution) { toast.error('Please select a bank'); return; }
    setLinking(true);
    setLinkStep('connecting');
    try {
      await fetch(`${API}/plaid/link-token`, { method: 'POST', credentials: 'include', headers: getAuthHeaders() });
      await new Promise(r => setTimeout(r, 2000));
      const institution = MOCK_INSTITUTIONS.find(i => i.id === selectedInstitution);
      const res = await fetch(`${API}/plaid/exchange-token`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({ institution_name: institution?.name || 'Demo Bank' })
      });
      if (!res.ok) throw new Error();
      setLinkStep('success');
      await new Promise(r => setTimeout(r, 1500));
      await fetchAccounts();
      toast.success('Demo bank account linked!');
      setLinkDialogOpen(false);
      resetDialog();
    } catch (err) { if (process.env.NODE_ENV !== 'production') console.error('Tink link error:', err); toast.error('Failed to link'); setLinkStep('choose'); }
    finally { setLinking(false); }
  };

  const handleDisconnect = async (accountId) => {
    try {
      const res = await fetch(`${API}/bank-accounts/${accountId}`, { method: 'DELETE', credentials: 'include', headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        setAccounts(accounts.filter(a => a.account_id !== accountId));
        const removed = data.transactions_removed || 0;
        toast.success(removed ? `Account disconnected (${removed} transactions removed)` : 'Account disconnected');
        // Notify other open pages (Dashboard, Spending, etc.) to refetch.
        window.dispatchEvent(new CustomEvent('flowvise:data-changed', { detail: { type: 'bank_disconnected' } }));
      }
    } catch (err) { if (process.env.NODE_ENV !== 'production') console.error('Disconnect error:', err); toast.error('Failed to disconnect'); }
  };

  const handleRefreshTink = async () => {
    setRefreshing(true);
    try {
      const res = await fetch(`${API}/tink/refresh`, { method: 'POST', credentials: 'include', headers: getAuthHeaders() });
      if (!res.ok) { const err = await res.json(); throw new Error(err.detail); }
      const data = await res.json();
      toast.success(data.message);
      await fetchAccounts();
    } catch (err) { toast.error(err.message || 'Failed to refresh'); }
    finally { setRefreshing(false); }
  };

  const resetDialog = () => { setLinkStep('choose'); setLinkMode(null); setSelectedInstitution(''); setTinkLinkUrl(null); };

  const getAccountIcon = (type) => {
    if (type === 'checking' || type === 'current') return <Landmark className="w-5 h-5" />;
    if (type === 'savings') return <Building className="w-5 h-5" />;
    if (type === 'credit') return <CreditCard className="w-5 h-5" />;
    return <Building className="w-5 h-5" />;
  };

  const totalBalance = accounts.reduce((sum, acc) => sum + (acc.balance || 0), 0);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="px-5 sm:px-8 lg:px-12 pt-8 lg:pt-10 pb-16" data-testid="bank-accounts-page">
        <div className="max-w-5xl mx-auto space-y-10">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="page-title">Bank Accounts</h1>
              <p className="text-muted-foreground mt-1">Connect your bank accounts to track spending automatically</p>
            </div>

            <Dialog open={linkDialogOpen} onOpenChange={(open) => { setLinkDialogOpen(open); if (!open) resetDialog(); }}>
              <div className="flex gap-2">
                <Button variant="outline" onClick={handleRefreshTink} disabled={refreshing} data-testid="refresh-tink-button">
                  <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                  {refreshing ? 'Syncing...' : 'Sync Tink'}
                </Button>
                <DialogTrigger asChild>
                  <Button className="btn-lift" data-testid="link-bank-button"><Plus className="w-4 h-4 mr-2" />Link Bank Account</Button>
                </DialogTrigger>
              </div>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle className="font-heading">Link Bank Account</DialogTitle>
                  <DialogDescription>Choose how to connect your bank</DialogDescription>
                </DialogHeader>

                {linkStep === 'choose' && !linkMode && (
                  <div className="space-y-3 py-4">
                    <Button className="w-full justify-start h-auto py-4 px-4" variant="outline"
                      onClick={() => setLinkMode('tink')} data-testid="choose-tink">
                      <div className="text-left">
                        <p className="font-medium">Connect via Tink</p>
                        <p className="text-xs text-muted-foreground mt-0.5">Securely connect to 3,400+ European banks via open banking</p>
                      </div>
                    </Button>
                    <Button className="w-full justify-start h-auto py-4 px-4" variant="outline"
                      onClick={() => setLinkMode('demo')} data-testid="choose-demo">
                      <div className="text-left">
                        <p className="font-medium">Use Demo Data</p>
                        <p className="text-xs text-muted-foreground mt-0.5">Add mock bank accounts with sample transactions</p>
                      </div>
                    </Button>
                  </div>
                )}

                {linkStep === 'choose' && linkMode === 'tink' && (
                  <div className="space-y-4 py-4">
                    <div className="bg-primary/5 border border-primary/20 p-4 rounded-lg text-sm">
                      <p className="font-medium text-primary mb-1">Tink Open Banking</p>
                      <p className="text-muted-foreground">You'll be redirected to Tink's secure portal to select your bank and authorize access to your accounts and transactions.</p>
                    </div>
                    <Button className="w-full" onClick={handleTinkLink} disabled={linking} data-testid="connect-tink-button">
                      {linking ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <ExternalLink className="w-4 h-4 mr-2" />}
                      Connect with Tink
                    </Button>
                    <button onClick={() => setLinkMode(null)} className="text-sm text-muted-foreground hover:underline w-full text-center">Back</button>
                  </div>
                )}

                {linkStep === 'choose' && linkMode === 'demo' && (
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Select your bank</Label>
                      <Select value={selectedInstitution} onValueChange={setSelectedInstitution}>
                        <SelectTrigger data-testid="bank-select"><SelectValue placeholder="Choose a bank..." /></SelectTrigger>
                        <SelectContent>
                          {MOCK_INSTITUTIONS.map(inst => (
                            <SelectItem key={inst.id} value={inst.id}>
                              <span className="flex items-center gap-2"><span>{inst.logo}</span><span>{inst.name}</span></span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="bg-muted/50 p-3 rounded-lg text-sm text-muted-foreground">
                      <p>This adds demo data for testing. Use Tink for real bank connections.</p>
                    </div>
                    <Button className="w-full" onClick={handleDemoLink} disabled={!selectedInstitution || linking} data-testid="confirm-link-button">
                      Add Demo Account
                    </Button>
                    <button onClick={() => setLinkMode(null)} className="text-sm text-muted-foreground hover:underline w-full text-center">Back</button>
                  </div>
                )}

                {linkStep === 'redirect' && tinkLinkUrl && (
                  <div className="py-6 text-center space-y-4">
                    <ExternalLink className="w-12 h-12 mx-auto text-primary" />
                    <p className="text-muted-foreground">Click below to securely connect your bank via Tink</p>
                    <a href={tinkLinkUrl} target="_blank" rel="noopener noreferrer">
                      <Button className="btn-lift" data-testid="open-tink-link">
                        <ExternalLink className="w-4 h-4 mr-2" />Open Tink Link
                      </Button>
                    </a>
                    <p className="text-xs text-muted-foreground">Opens in a new tab. Return here after connecting.</p>
                  </div>
                )}

                {linkStep === 'connecting' && (
                  <div className="py-8 text-center space-y-4">
                    <Loader2 className="w-12 h-12 animate-spin mx-auto text-primary" />
                    <p className="text-muted-foreground">Connecting to your bank...</p>
                  </div>
                )}

                {linkStep === 'success' && (
                  <div className="py-8 text-center space-y-4">
                    <CheckCircle className="w-12 h-12 mx-auto text-cyan-700" />
                    <p className="font-medium">Successfully connected!</p>
                  </div>
                )}
              </DialogContent>
            </Dialog>
          </div>

          {/* Summary Card */}
          <Card data-testid="balance-summary-card">
            <CardHeader>
              <CardTitle className="font-heading">Total Balance</CardTitle>
              <CardDescription>Combined balance across all accounts</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="money text-4xl">{fc(totalBalance)}</div>
            </CardContent>
          </Card>

          {/* Accounts List */}
          <Card data-testid="accounts-list-card">
            <CardHeader>
              <CardTitle className="font-heading">Connected Accounts</CardTitle>
              <CardDescription>{accounts.length} account{accounts.length !== 1 ? 's' : ''} linked</CardDescription>
            </CardHeader>
            <CardContent>
              {loading && (
                <div className="py-8 text-center text-muted-foreground">Loading accounts...</div>
              )}
              {!loading && accounts.length === 0 && (
                <div className="py-8 text-center">
                  <Building className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
                  <p className="text-muted-foreground">No bank accounts connected yet</p>
                  <p className="text-sm text-muted-foreground mt-1">Link a bank account to start tracking your spending</p>
                </div>
              )}
              {!loading && accounts.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Account</TableHead>
                      <TableHead>Bank</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Balance</TableHead>
                      <TableHead></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {accounts.map(account => (
                      <TableRow key={account.account_id} data-testid={`account-row-${account.account_id}`}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                              {getAccountIcon(account.type)}
                            </div>
                            <div>
                              <p className="font-medium">{account.name}</p>
                              <p className="text-xs text-muted-foreground">
                                ****{account.mask}
                                {account.source === 'tink' && <Badge variant="outline" className="ml-2 text-[10px] py-0">Tink</Badge>}
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>{account.institution}</TableCell>
                        <TableCell><Badge variant="secondary" className="capitalize">{account.type}</Badge></TableCell>
                        <TableCell className="text-right font-medium">{fc(account.balance)}</TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm" onClick={() => handleDisconnect(account.account_id)}
                            className="text-muted-foreground hover:text-destructive" data-testid={`disconnect-${account.account_id}`}>
                            <Unlink className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
