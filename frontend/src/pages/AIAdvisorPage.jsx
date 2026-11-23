import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Sidebar } from '../components/Sidebar';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Separator } from '../components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Bot,
  Send,
  AlertTriangle,
  Sparkles,
  Clock,
  ChevronDown,
  ChevronUp,
  Loader2
} from 'lucide-react';
import { formatCurrency, cn } from '../lib/utils';
import { useCurrency } from '../contexts/CurrencyContext';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AIAdvisorPage() {
  const { getAuthHeaders } = useAuth();
  const { fc } = useCurrency();
  const [question, setQuestion] = useState('');
  const [advice, setAdvice] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(true);
  const [expandedHistory, setExpandedHistory] = useState(null);
  const [advisorUnavailable, setAdvisorUnavailable] = useState(null);

  const fetchHistory = useCallback(async () => {
    try {
      const response = await fetch(`${API}/advisor/history`, {
        credentials: 'include',
        headers: getAuthHeaders()
      });
      if (response.ok) {
        setHistory(await response.json());
      }
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('History load failed:', err);
    } finally {
      setHistoryLoading(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleGetAdvice = async () => {
    setLoading(true);
    setAdvice(null);
    setAdvisorUnavailable(null);

    try {
      const response = await fetch(`${API}/advisor/advice`, {
        method: 'POST',
        credentials: 'include',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          question: question || null,
          context: null
        })
      });

      const text = await response.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) { /* non-json */ }

      if (response.status === 503) {
        const detail = typeof data.detail === 'string'
          ? data.detail
          : 'AI advisor is unavailable. Set OPENAI_API_KEY on the backend to enable.';
        setAdvisorUnavailable(detail);
        toast.error(detail);
        return;
      }

      if (!response.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : 'Failed to get advice';
        throw new Error(detail);
      }

      setAdvice(data);
      setQuestion('');
      await fetchHistory();
    } catch (err) {
      toast.error(err.message || 'Failed to get AI advice. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAcceptDisclaimer = () => {
    setDisclaimerAccepted(true);
    setShowDisclaimer(false);
  };

  const formatAdviceText = (text) => {
    if (!text) return null;
    
    // Split by sections and format
    const sections = text.split(/(?=##|###|\*\*[A-Z])/);
    
    return sections.map((section, index) => {
      const sectionKey = `section-${index}-${section.slice(0, 20).replace(/\W/g, '')}`;
      // Handle headers
      if (section.startsWith('##')) {
        const headerMatch = section.match(/^##\s*(.+?)(?:\n|$)/);
        if (headerMatch) {
          const header = headerMatch[1].replace(/\*\*/g, '');
          const content = section.replace(/^##\s*.+?\n/, '');
          return (
            <div key={sectionKey} className="mb-4">
              <h3 className="font-heading font-semibold text-lg mb-2">{header}</h3>
              <div className="text-muted-foreground whitespace-pre-wrap">{content}</div>
            </div>
          );
        }
      }
      
      // Handle bold text sections
      if (section.startsWith('**')) {
        const boldMatch = section.match(/^\*\*(.+?)\*\*/);
        if (boldMatch) {
          return (
            <p key={sectionKey} className="mb-2">
              <strong>{boldMatch[1]}</strong>
              {section.replace(/^\*\*.+?\*\*/, '')}
            </p>
          );
        }
      }
      
      return <p key={sectionKey} className="mb-2 whitespace-pre-wrap">{section}</p>;
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />

      {/* Disclaimer Dialog */}
      <Dialog open={showDisclaimer && !disclaimerAccepted} onOpenChange={setShowDisclaimer}>
        <DialogContent className="sm:max-w-lg" data-testid="ai-disclaimer-dialog">
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              AI Financial Advice Disclaimer
            </DialogTitle>
            <DialogDescription>
              Important information about AI-generated financial advice
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 space-y-4">
            <div className="bg-amber-50 border border-amber-200 p-4 rounded-lg space-y-3 text-sm">
              <p className="font-medium text-amber-800">Please understand:</p>
              <ul className="space-y-2 text-amber-700">
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>This AI advisor provides educational information only, not personalized financial advice.</span>
                </li>
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>AI recommendations may not account for your complete financial situation.</span>
                </li>
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>Investing based on AI advice is entirely at your own risk.</span>
                </li>
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>Always consult a licensed financial advisor for major financial decisions.</span>
                </li>
              </ul>
            </div>

            <p className="text-sm text-muted-foreground">
              By clicking "I Understand", you acknowledge that you understand the limitations of AI-generated
              financial advice and that any actions taken based on this advice are your own responsibility.
            </p>
          </div>

          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => window.history.back()}>
              Go Back
            </Button>
            <Button onClick={handleAcceptDisclaimer} data-testid="accept-ai-disclaimer">
              I Understand
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <main className="lg:ml-60 pt-16 lg:pt-0 p-6" data-testid="ai-advisor-page">
        <div className="max-w-5xl mx-auto space-y-6">
          {/* Header */}
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-semibold tracking-tight flex items-center gap-3">
              <Bot className="w-8 h-8 text-primary" />
              AI Financial Advisor
            </h1>
            <p className="text-muted-foreground mt-1">
              Get personalized financial advice powered by AI
            </p>
          </div>

          {disclaimerAccepted && (
            <>
              {advisorUnavailable && (
                <Card
                  className="border-amber-200 bg-amber-50"
                  data-testid="advisor-unavailable-banner"
                >
                  <CardContent className="py-4 flex items-start gap-3 text-sm text-amber-800">
                    <AlertTriangle className="w-5 h-5 mt-0.5 flex-shrink-0 text-amber-600" />
                    <div>
                      <p className="font-medium">AI Advisor unavailable</p>
                      <p className="mt-1 text-amber-700">{advisorUnavailable}</p>
                      <p className="mt-2 text-amber-700">
                        Configure <code className="text-xs">OPENAI_API_KEY</code> in the
                        backend environment (optional <code className="text-xs">OPENAI_BASE_URL</code>,{' '}
                        <code className="text-xs">OPENAI_MODEL</code>) and retry.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Input Card */}
              <Card data-testid="advice-input-card">
                <CardHeader>
                  <CardTitle className="font-heading">Ask for Advice</CardTitle>
                  <CardDescription>
                    Ask a specific question or get a general financial assessment
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <Textarea
                      placeholder="e.g., Should I invest in ETFs given my current financial situation? What's the best way to build an emergency fund?"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      rows={3}
                      data-testid="advice-question-input"
                    />
                    <div className="flex justify-end">
                      <Button
                        onClick={handleGetAdvice}
                        disabled={loading}
                        className="btn-lift"
                        data-testid="get-advice-button"
                      >
                        {loading ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Analyzing...
                          </>
                        ) : (
                          <>
                            <Sparkles className="w-4 h-4 mr-2" />
                            {question ? 'Get Advice' : 'Get General Assessment'}
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Current Advice */}
              {advice && (
                <Card data-testid="advice-response-card">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="font-heading flex items-center gap-2">
                        <Bot className="w-5 h-5 text-primary" />
                        AI Advice
                      </CardTitle>
                      <Badge variant="secondary">
                        Confidence: {Math.round((advice.confidence_level || 0) * 100)}%
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {/* Financial Snapshot */}
                    <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-muted/50 rounded-lg">
                      <div>
                        <p className="text-sm text-muted-foreground">Income</p>
                        <p className="font-semibold">{fc(advice.financial_snapshot?.income || 0)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Safe to Invest</p>
                        <p className="font-semibold">{fc(advice.financial_snapshot?.safe_to_invest || 0)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Status</p>
                        <Badge className={cn(
                          advice.financial_snapshot?.status === 'excellent' && 'bg-green-100 text-green-700',
                          advice.financial_snapshot?.status === 'good' && 'bg-emerald-100 text-emerald-700',
                          advice.financial_snapshot?.status === 'moderate' && 'bg-amber-100 text-amber-700',
                          advice.financial_snapshot?.status === 'not_recommended' && 'bg-red-100 text-red-700'
                        )}>
                          {advice.financial_snapshot?.status?.replace('_', ' ') || 'Unknown'}
                        </Badge>
                      </div>
                    </div>

                    {/* Advice Content */}
                    <ScrollArea className="h-[400px] pr-4">
                      <div className="prose prose-sm max-w-none">
                        {formatAdviceText(advice.advice)}
                      </div>
                    </ScrollArea>

                    {/* Disclaimer */}
                    <div className="disclaimer-banner mt-6 p-4 rounded-lg">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                        <p className="text-sm text-amber-700">{advice.disclaimer}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* History */}
              <Card data-testid="advice-history-card">
                <CardHeader>
                  <CardTitle className="font-heading flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Advice History
                  </CardTitle>
                  <CardDescription>Your previous AI consultations</CardDescription>
                </CardHeader>
                <CardContent>
                  {historyLoading && (
                    <div className="py-8 text-center text-muted-foreground">Loading history...</div>
                  )}
                  {!historyLoading && history.length === 0 && (
                    <div className="py-8 text-center">
                      <Bot className="w-12 h-12 mx-auto text-muted-foreground/50 mb-4" />
                      <p className="text-muted-foreground">No advice history yet</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        Get your first AI financial assessment above
                      </p>
                    </div>
                  )}
                  {!historyLoading && history.length > 0 && (
                    <div className="space-y-4">
                      {history.slice(0, 10).map((item, index) => (
                        <div key={item.advice_id || index} className="border rounded-lg">
                          <button
                            onClick={() => setExpandedHistory(expandedHistory === index ? null : index)}
                            className="w-full p-4 flex items-center justify-between text-left hover:bg-muted/50 transition-colors"
                            data-testid={`history-item-${index}`}
                          >
                            <div>
                              <p className="font-medium">
                                {item.question || 'General Assessment'}
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {new Date(item.created_at).toLocaleDateString()}
                              </p>
                            </div>
                            {expandedHistory === index ? (
                              <ChevronUp className="w-5 h-5 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="w-5 h-5 text-muted-foreground" />
                            )}
                          </button>
                          {expandedHistory === index && (
                            <div className="px-4 pb-4">
                              <Separator className="mb-4" />
                              <ScrollArea className="h-[200px]">
                                <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                                  {item.response}
                                </div>
                              </ScrollArea>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
