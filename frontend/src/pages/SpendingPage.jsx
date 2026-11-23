import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import { Plus, TrendingDown, Calendar, Receipt, Tag, X } from 'lucide-react';
import { cn } from '../lib/utils';
import { toast } from 'sonner';
import { TransactionsTable } from '../components/TransactionsTable';
import { SpendingCategoryChart, MonthlySpendingChart } from '../components/SpendingCharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DEFAULT_CATEGORIES = [
  'Food & Dining', 'Shopping', 'Transportation', 'Entertainment',
  'Bills & Utilities', 'Healthcare', 'Personal Care', 'Education', 'Travel', 'Other'
];

export default function SpendingPage() {
  const { getAuthHeaders } = useAuth();
  const { fc, symbol } = useCurrency();
  const [transactions, setTransactions] = useState([]);
  const [spendingData, setSpendingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);
  const [activeTab, setActiveTab] = useState('all');
  const [addingToCategory, setAddingToCategory] = useState(null);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [showNewCategoryInput, setShowNewCategoryInput] = useState(false);
  const [newExpense, setNewExpense] = useState({ amount: '', description: '', date: new Date().toISOString().split('T')[0] });
  const [visibleCount, setVisibleCount] = useState(5);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API}/categories`, { credentials: 'include', headers: getAuthHeaders() });
      if (res.ok) { const data = await res.json(); setCategories(data.all || DEFAULT_CATEGORIES); }
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Categories fetch failed:', err);
    }
  }, [getAuthHeaders]);

  const fetchData = useCallback(async () => {
    try {
      const [txnRes, summaryRes] = await Promise.all([
        fetch(`${API}/transactions`, { credentials: 'include', headers: getAuthHeaders() }),
        fetch(`${API}/analysis/spending-summary`, { credentials: 'include', headers: getAuthHeaders() })
      ]);
      if (txnRes.ok) setTransactions(await txnRes.json());
      if (summaryRes.ok) setSpendingData(await summaryRes.json());
    } catch (err) { if (process.env.NODE_ENV !== 'production') console.error('Spending fetch error:', err); toast.error('Failed to fetch data'); }
    finally { setLoading(false); }
  }, [getAuthHeaders]);

  useEffect(() => {
    fetchData();
    fetchCategories();
    const onChange = () => { fetchData(); fetchCategories(); };
    window.addEventListener('flowvise:data-changed', onChange);
    window.addEventListener('focus', onChange);
    return () => {
      window.removeEventListener('flowvise:data-changed', onChange);
      window.removeEventListener('focus', onChange);
    };
  }, [fetchData, fetchCategories]);

  const handleAddCategory = async () => {
    const name = newCategoryName.trim();
    if (!name) return;
    try {
      const res = await fetch(`${API}/categories`, { method: 'POST', credentials: 'include', headers: getAuthHeaders(), body: JSON.stringify({ name }) });
      if (!res.ok) { const err = await res.json(); toast.error(err.detail); return; }
      toast.success(`"${name}" added`);
      setNewCategoryName('');
      setShowNewCategoryInput(false);
      await fetchCategories();
      setActiveTab(name);
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Add category failed:', err);
      toast.error('Failed');
    }
  };

  const handleRemoveCategory = async (name) => {
    // Remove from API (works for custom categories)
    try {
      await fetch(`${API}/categories/${encodeURIComponent(name)}`, { method: 'DELETE', credentials: 'include', headers: getAuthHeaders() });
    } catch (err) {
      // Ignore — likely a default category that has no DB row to delete.
      if (process.env.NODE_ENV !== 'production') console.debug('Category delete (default):', err);
    }
    // Remove locally regardless
    setCategories(prev => prev.filter(c => c !== name));
    if (activeTab === name) { setActiveTab('all'); setVisibleCount(5); }
    toast.success(`"${name}" removed`);
  };

  const handleAddExpense = async () => {
    if (!newExpense.amount || !newExpense.description) { toast.error('Fill in amount and description'); return; }
    const category = addingToCategory || activeTab;
    try {
      const res = await fetch(`${API}/transactions`, {
        method: 'POST', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify({ ...newExpense, amount: parseFloat(newExpense.amount), category, type: 'expense' })
      });
      if (!res.ok) throw new Error();
      toast.success('Expense added');
      setAddingToCategory(null);
      setNewExpense({ amount: '', description: '', date: new Date().toISOString().split('T')[0] });
      await fetchData();
    } catch (err) { if (process.env.NODE_ENV !== 'production') console.error('Add expense error:', err); toast.error('Failed'); }
  };

  const handleDeleteTransaction = async (id) => {
    try {
      const res = await fetch(`${API}/transactions/${id}`, { method: 'DELETE', credentials: 'include', headers: getAuthHeaders() });
      if (res.ok) { setTransactions(transactions.filter(t => t.transaction_id !== id)); toast.success('Deleted'); await fetchData(); }
    } catch (err) { if (process.env.NODE_ENV !== 'production') console.error('Delete transaction error:', err); toast.error('Failed'); }
  };

  const filteredTransactions = activeTab === 'all' ? transactions : transactions.filter(t => t.category === activeTab);
  const categoryChartData = spendingData?.by_category ? Object.entries(spendingData.by_category).map(([name, value]) => ({ name, value })) : [];
  const monthlyChartData = spendingData?.by_month ? Object.entries(spendingData.by_month).map(([month, amount]) => ({ month: month.slice(5), amount })).slice(-6) : [];

  const getCategoryTotal = (cat) => {
    return transactions.filter(t => t.category === cat && t.type === 'expense').reduce((sum, t) => sum + (t.amount || 0), 0);
  };

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="lg:ml-60 pt-16 lg:pt-0 p-6" data-testid="spending-page">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header */}
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-semibold tracking-tight">Spending Tracker</h1>
            <p className="text-muted-foreground mt-1 text-sm">Organize expenses by category</p>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card data-testid="total-spending-card"><CardHeader className="flex flex-row items-center justify-between pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Total Spending</CardTitle><TrendingDown className="w-4 h-4 text-destructive" /></CardHeader><CardContent><div className="text-xl font-semibold font-heading">{fc(spendingData?.total_spending || 0)}</div></CardContent></Card>
            <Card data-testid="avg-monthly-card"><CardHeader className="flex flex-row items-center justify-between pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Monthly Average</CardTitle><Calendar className="w-4 h-4 text-muted-foreground" /></CardHeader><CardContent><div className="text-xl font-semibold font-heading">{fc(spendingData?.average_monthly_spending || 0)}</div></CardContent></Card>
            <Card data-testid="transaction-count-card"><CardHeader className="flex flex-row items-center justify-between pb-2"><CardTitle className="text-sm font-medium text-muted-foreground">Transactions</CardTitle><Receipt className="w-4 h-4 text-primary" /></CardHeader><CardContent><div className="text-xl font-semibold font-heading">{spendingData?.transaction_count || 0}</div></CardContent></Card>
          </div>

          {/* Category Tabs */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 overflow-x-auto pb-2" data-testid="category-tabs">
              <button onClick={() => { setActiveTab('all'); setVisibleCount(5); }}
                className={cn("px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
                  activeTab === 'all' ? "bg-primary text-primary-foreground" : "bg-muted/50 text-muted-foreground hover:text-foreground hover:bg-muted"
                )} data-testid="tab-all">
                All
              </button>
              {categories.map(cat => (
                <button key={cat} onClick={() => { setActiveTab(cat); setVisibleCount(5); }}
                  className={cn("group flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all relative",
                    activeTab === cat ? "bg-primary text-primary-foreground" : "bg-muted/50 text-muted-foreground hover:text-foreground hover:bg-muted"
                  )} data-testid={`tab-${cat}`}>
                  {!DEFAULT_CATEGORIES.includes(cat) && <Tag className="w-3 h-3" />}
                  {cat}
                  <span onClick={(e) => { e.stopPropagation(); handleRemoveCategory(cat); }}
                    className="ml-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer hover:text-destructive" data-testid={`remove-tab-${cat}`}>
                    <X className="w-3 h-3" />
                  </span>
                </button>
              ))}
              {/* Add new category tab */}
              {!showNewCategoryInput ? (
                <button onClick={() => setShowNewCategoryInput(true)}
                  className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 border border-dashed border-border transition-all"
                  data-testid="add-category-tab">
                  <Plus className="w-3 h-3" /> New
                </button>
              ) : (
                <div className="flex items-center gap-1">
                  <Input className="h-8 w-36 text-sm" placeholder="Category name..."
                    value={newCategoryName} onChange={(e) => setNewCategoryName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleAddCategory(); if (e.key === 'Escape') { setShowNewCategoryInput(false); setNewCategoryName(''); } }}
                    autoFocus data-testid="new-category-input" />
                  <Button size="sm" variant="ghost" className="h-8 px-2" onClick={handleAddCategory}>Add</Button>
                  <Button size="sm" variant="ghost" className="h-8 px-2" onClick={() => { setShowNewCategoryInput(false); setNewCategoryName(''); }}><X className="w-3 h-3" /></Button>
                </div>
              )}
            </div>

            {/* Active tab content */}
            {activeTab !== 'all' && (
              <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg border border-border/50">
                <div className="flex items-center gap-3">
                  <Badge variant="outline">{activeTab}</Badge>
                  <span className="text-sm text-muted-foreground">{filteredTransactions.length} transactions · {fc(getCategoryTotal(activeTab))} total</span>
                </div>
                <Button size="sm" variant="outline" onClick={() => setAddingToCategory(activeTab)} data-testid="add-to-category-button">
                  <Plus className="w-3 h-3 mr-1" /> Add Expense
                </Button>
              </div>
            )}

            {activeTab === 'all' && (
              <div className="flex justify-end">
                <Button size="sm" variant="outline" onClick={() => setAddingToCategory('__pick__')} data-testid="add-transaction-button">
                  <Plus className="w-3 h-3 mr-1" /> Add Expense
                </Button>
              </div>
            )}
          </div>

          {/* Charts (only on All tab) */}
          {activeTab === 'all' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <SpendingCategoryChart data={categoryChartData} fc={fc} />
              <MonthlySpendingChart data={monthlyChartData} fc={fc} symbol={symbol} />
            </div>
          )}

          {/* Transactions */}
          <Card data-testid="transactions-table-card">
            <CardHeader>
              <CardTitle className="font-heading">{activeTab === 'all' ? 'All Transactions' : activeTab}</CardTitle>
              <CardDescription>{filteredTransactions.length} transaction{filteredTransactions.length !== 1 ? 's' : ''}</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? <div className="py-8 text-center text-muted-foreground">Loading...</div>
                : (
                  <>
                    <TransactionsTable transactions={filteredTransactions.slice(0, visibleCount)} onDelete={handleDeleteTransaction} fc={fc} />
                    {filteredTransactions.length > visibleCount && (
                      <div className="flex justify-center mt-4">
                        <Button variant="outline" size="sm" onClick={() => setVisibleCount(prev => prev + 20)} data-testid="show-more-transactions">
                          Show More ({filteredTransactions.length - visibleCount} remaining)
                        </Button>
                      </div>
                    )}
                    {filteredTransactions.length === 0 && (
                      <div className="py-8 text-center text-muted-foreground text-sm">No transactions in this category</div>
                    )}
                  </>
                )}
            </CardContent>
          </Card>

          {/* Add Expense Dialog */}
          <Dialog open={!!addingToCategory} onOpenChange={(open) => { if (!open) setAddingToCategory(null); }}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="font-heading">Add Expense</DialogTitle>
                <DialogDescription>
                  {addingToCategory === '__pick__' ? 'Select a category and add your expense' : `Adding to ${addingToCategory}`}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                {addingToCategory === '__pick__' && (
                  <div className="space-y-2">
                    <Label>Category</Label>
                    <Select onValueChange={(v) => setAddingToCategory(v)}>
                      <SelectTrigger data-testid="expense-category-select"><SelectValue placeholder="Select category..." /></SelectTrigger>
                      <SelectContent>
                        {categories.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>Amount</Label><Input data-testid="expense-amount-input" type="number" step="0.01" placeholder="0.00" value={newExpense.amount} onChange={(e) => setNewExpense({ ...newExpense, amount: e.target.value })} /></div>
                  <div className="space-y-2"><Label>Date</Label><Input data-testid="expense-date-input" type="date" value={newExpense.date} onChange={(e) => setNewExpense({ ...newExpense, date: e.target.value })} /></div>
                </div>
                <div className="space-y-2"><Label>Description</Label><Input data-testid="expense-description-input" placeholder="e.g., Grocery shopping" value={newExpense.description} onChange={(e) => setNewExpense({ ...newExpense, description: e.target.value })} /></div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setAddingToCategory(null)}>Cancel</Button>
                <Button onClick={handleAddExpense} disabled={addingToCategory === '__pick__'} data-testid="confirm-add-expense">Add</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </main>
    </div>
  );
}
