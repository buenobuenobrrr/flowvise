import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { Badge } from './ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import {
  AlertTriangle, Shield, TrendingUp, DollarSign, Info, CheckCircle, ExternalLink, BookOpen, Building, Globe
} from 'lucide-react';
import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from './ui/dialog';
import { getRiskColor, cn } from '../lib/utils';

function LearnMorePanel({ option, fc }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="link" size="sm" className="text-primary p-0 h-auto"
        onClick={() => setOpen(true)}
        data-testid={`learn-more-${option.type.toLowerCase().replace(/[\s/()]+/g, '-')}`}>
        <BookOpen className="w-3.5 h-3.5 mr-1" /> Learn More
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg" data-testid={`learn-dialog-${option.type.toLowerCase().replace(/[\s/()]+/g, '-')}`}>
          <DialogHeader>
            <DialogTitle className="font-heading flex items-center gap-2"><BookOpen className="w-5 h-5 text-primary" />{option.type}</DialogTitle>
            <DialogDescription>Educational overview</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div><h4 className="font-medium text-sm mb-1">What is it?</h4><p className="text-sm text-muted-foreground leading-relaxed">{option.learn_more_summary || option.description}</p></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-muted/50 rounded-lg"><p className="text-xs text-muted-foreground">Typical Return</p><p className="font-semibold text-sm">{option.typical_return}</p></div>
              <div className="p-3 bg-muted/50 rounded-lg"><p className="text-xs text-muted-foreground">Risk Score</p><p className="font-semibold text-sm">{option.risk_score}/10</p></div>
              <div className="p-3 bg-muted/50 rounded-lg"><p className="text-xs text-muted-foreground">Min. Investment</p><p className="font-semibold text-sm">{fc(option.min_investment)}</p></div>
              <div className="p-3 bg-muted/50 rounded-lg"><p className="text-xs text-muted-foreground">Region</p><p className="font-semibold text-sm flex items-center gap-1"><Globe className="w-3.5 h-3.5" /> Europe</p></div>
            </div>
            {option.where_to_invest?.length > 0 && (
              <div><h4 className="font-medium text-sm mb-2">Where to invest</h4>
                <div className="space-y-2">
                  {option.where_to_invest.map((place, idx) => (
                    <div key={place.name} className="flex items-start gap-3 p-3 border rounded-lg">
                      <div className="w-8 h-8 rounded-md bg-secondary flex items-center justify-center flex-shrink-0 mt-0.5">
                        {place.type === 'broker' ? <TrendingUp className="w-4 h-4 text-primary" /> : <Building className="w-4 h-4 text-primary" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2"><p className="font-medium text-sm">{place.name}</p><Badge variant="outline" className="text-xs capitalize">{place.type}</Badge></div>
                        <p className="text-xs text-muted-foreground mt-0.5">{place.note}</p>
                      </div>
                      {place.url && <a href={place.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 flex-shrink-0"><ExternalLink className="w-4 h-4" /></a>}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {option.learn_more_url && <a href={option.learn_more_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-sm text-primary hover:underline"><ExternalLink className="w-4 h-4" />Read full guide on Investopedia</a>}
            <div className="bg-amber-50 border border-amber-200 p-3 rounded-lg"><p className="text-xs text-amber-700">We are not brokers. This is educational information only. Always do your own research before investing.</p></div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function InvestmentPortfolioTabs({ investmentOptions, fc }) {
  return (
    <Tabs defaultValue="conservative" className="space-y-6">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="conservative" data-testid="tab-conservative"><Shield className="w-4 h-4 mr-2" /> Conservative</TabsTrigger>
        <TabsTrigger value="moderate" data-testid="tab-moderate"><TrendingUp className="w-4 h-4 mr-2" /> Moderate</TabsTrigger>
        <TabsTrigger value="aggressive" data-testid="tab-aggressive"><DollarSign className="w-4 h-4 mr-2" /> Aggressive</TabsTrigger>
      </TabsList>
      {Object.entries(investmentOptions.options).map(([key, portfolio]) => (
        <TabsContent key={key} value={key}>
          <Card data-testid={`portfolio-${key}`}>
            <CardHeader>
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div><CardTitle className="font-heading">{portfolio.title}</CardTitle><CardDescription>Expected: {portfolio.expected_return}</CardDescription></div>
                <div className="text-right">
                  <Badge className={getRiskColor(portfolio.risk_level)}>{portfolio.risk_level} Risk</Badge>
                  <p className="text-sm text-muted-foreground mt-1">Risk Probability: {Math.round(portfolio.risk_probability * 100)}%</p>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-6">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-muted-foreground">Risk Level</span>
                  <span className="font-medium">{Math.round(portfolio.risk_probability * 100)}% probability of loss</span>
                </div>
                <Progress value={portfolio.risk_probability * 100} className={cn("h-3",
                  key === 'conservative' && "[&>div]:bg-green-500",
                  key === 'moderate' && "[&>div]:bg-amber-500",
                  key === 'aggressive' && "[&>div]:bg-red-500"
                )} />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {portfolio.options.map((option) => (
                  <div key={`${key}-${option.type}`} className="investment-card group" data-testid={`option-${option.type.toLowerCase().replace(/[\s/()]+/g, '-')}`}>
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-sm">{option.type}</h4>
                      <Badge variant="outline" className="flex-shrink-0 text-xs">{option.typical_return}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mb-3 leading-relaxed">{option.description}</p>
                    <div className="flex items-center justify-between text-xs mb-3">
                      <span className="text-muted-foreground">Min: {fc(option.min_investment)}</span>
                      <span className="text-muted-foreground">Risk: <span className="font-medium">{option.risk_score}/10</span></span>
                    </div>
                    {option.where_to_invest?.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {option.where_to_invest.slice(0, 3).map((place) => <Badge key={place.name} variant="secondary" className="text-xs">{place.name}</Badge>)}
                      </div>
                    )}
                    <div className="flex items-center justify-between pt-2 border-t border-border/50">
                      <LearnMorePanel option={option} fc={fc} />
                      {option.where_to_invest?.[0]?.url && (
                        <a href={option.where_to_invest[0].url} target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1">
                          Visit {option.where_to_invest[0].name}<ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      ))}
    </Tabs>
  );
}

export function BankSafeOptions({ options, fc }) {
  if (!options) return null;
  return (
    <Card data-testid="bank-safe-options">
      <CardHeader>
        <div className="flex items-center gap-2"><Shield className="w-5 h-5 text-primary" /><CardTitle className="font-heading">Bank-Offered Safe Options</CardTitle></div>
        <CardDescription>Low-risk options typically offered by European banks</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {options.map((option) => (
            <div key={option.type} className="p-4 border rounded-lg">
              <div className="flex items-center gap-2 mb-2"><CheckCircle className="w-5 h-5 text-green-500" /><h4 className="font-medium text-sm">{option.type}</h4></div>
              <p className="text-sm text-muted-foreground mb-3 leading-relaxed">{option.description}</p>
              <div className="flex justify-between text-sm mb-3"><span className="text-muted-foreground">Typical APY</span><span className="font-medium text-green-600">{option.typical_apy}</span></div>
              {option.recommended_banks && (
                <div className="mb-3"><p className="text-xs text-muted-foreground mb-1.5">Recommended:</p><div className="flex flex-wrap gap-1">{option.recommended_banks.map((bank) => <Badge key={bank} variant="secondary" className="text-xs">{bank}</Badge>)}</div></div>
              )}
              {option.learn_more_url && (
                <div className="pt-2 border-t border-border/50">
                  <a href={option.learn_more_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline flex items-center gap-1"><BookOpen className="w-3.5 h-3.5" />Learn More</a>
                  {option.learn_more_summary && <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{option.learn_more_summary}</p>}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-muted/50 rounded-lg flex items-start gap-2">
          <Info className="w-4 h-4 text-muted-foreground mt-0.5" />
          <p className="text-sm text-muted-foreground">Contact your bank for current rates. EU Deposit Guarantee protects up to EUR 100,000 per depositor per bank.</p>
        </div>
      </CardContent>
    </Card>
  );
}
