import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { LanguagePicker } from '../components/LanguagePicker';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Separator } from '../components/ui/separator';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Leaf, TrendingUp, Shield, ArrowLeft, Mail, Loader2, KeyRound, Sparkles } from 'lucide-react';
import { CodeInput, AuthError, DemoCodeBanner } from '../components/AuthComponents';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const LOGO_URL = 'https://customer-assets.emergentagent.com/job_money-brain-ai/artifacts/qw0mtrax_image_2026-04-27_214300149.png';
const EMPTY_CODE = ['', '', '', '', '', ''];

// ─── Verification Screen ──────────────────────────────
function VerificationScreen({ email, demoCode, error, isLoading, onVerify, onResend, onBack }) {
  const [codeDigits, setCodeDigits] = useState(EMPTY_CODE);
  const inputRefs = useRef([]);

  const handleVerify = async () => {
    const code = codeDigits.join('');
    if (code.length !== 6) return;
    const success = await onVerify(code);
    if (!success) {
      setCodeDigits([...EMPTY_CODE]);
      inputRefs.current[0]?.focus();
    }
  };

  const handleResend = async () => {
    await onResend();
    setCodeDigits([...EMPTY_CODE]);
    inputRefs.current[0]?.focus();
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="absolute top-4 right-4"><LanguagePicker /></div>
      <Card className="w-full max-w-md" data-testid="verification-card">
        <CardHeader className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-primary/10 mx-auto mb-2">
            <Mail className="w-7 h-7 text-primary" />
          </div>
          <CardTitle className="font-heading text-xl">Verify Your Email</CardTitle>
          <CardDescription>We sent a 6-digit code to <strong>{email}</strong></CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <AuthError message={error} />
          <DemoCodeBanner code={demoCode} />
          <CodeInput digits={codeDigits} onChange={setCodeDigits} inputRefs={inputRefs} testIdPrefix="code" />
          <Button onClick={handleVerify} disabled={isLoading || codeDigits.join('').length !== 6}
            className="w-full btn-lift" data-testid="verify-button">
            {isLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Verifying...</> : 'Verify Email'}
          </Button>
          <div className="flex items-center justify-between text-sm">
            <button onClick={onBack} className="text-muted-foreground hover:text-foreground flex items-center gap-1" data-testid="back-to-auth">
              <ArrowLeft className="w-4 h-4" /> Back
            </button>
            <button onClick={handleResend} className="text-primary hover:underline" data-testid="resend-code-button">Resend Code</button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Password Reset Flow ──────────────────────────────
function PasswordResetFlow({ error, isLoading, initialEmail, onRequestCode, onResetPassword, onExit, setError }) {
  const [step, setStep] = useState('email');
  const [email, setEmail] = useState(initialEmail || '');
  const [demoCode, setDemoCode] = useState('');
  const [codeDigits, setCodeDigits] = useState(EMPTY_CODE);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const inputRefs = useRef([]);

  const handleSendCode = async () => {
    if (!email) { setError('Please enter your email'); return; }
    const result = await onRequestCode(email);
    if (result) {
      if (result.demo_code) setDemoCode(result.demo_code);
      setStep('code');
    }
  };

  const handleVerifyCode = () => {
    if (codeDigits.join('').length !== 6) { setError('Please enter all 6 digits'); return; }
    setStep('newpass');
    setError('');
  };

  const handleReset = async () => {
    if (newPassword.length < 6) { setError('Password must be at least 6 characters'); return; }
    if (newPassword !== confirmPassword) { setError('Passwords do not match'); return; }
    const success = await onResetPassword(email, codeDigits.join(''), newPassword);
    if (success) setStep('done');
  };

  const titles = { email: 'Reset Password', code: 'Enter Reset Code', newpass: 'Set New Password', done: 'Password Reset!' };
  const subtitles = { email: 'Enter your email to receive a reset code', code: `We sent a code to ${email}`,
    newpass: 'Choose a strong new password', done: 'Your password has been updated successfully' };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="absolute top-4 right-4"><LanguagePicker /></div>
      <Card className="w-full max-w-md" data-testid="reset-password-card">
        <CardHeader className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-primary/10 mx-auto mb-2">
            <KeyRound className="w-7 h-7 text-primary" />
          </div>
          <CardTitle className="font-heading text-xl">{titles[step]}</CardTitle>
          <CardDescription>{subtitles[step]}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <AuthError message={error} />

          {step === 'email' && (
            <>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input data-testid="reset-email-input" type="email" placeholder="you@example.com"
                  value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <Button onClick={handleSendCode} disabled={isLoading} className="w-full" data-testid="send-reset-code-button">
                {isLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Sending...</> : 'Send Reset Code'}
              </Button>
            </>
          )}

          {step === 'code' && (
            <>
              <DemoCodeBanner code={demoCode} testId="reset-demo-code" />
              <CodeInput digits={codeDigits} onChange={setCodeDigits} inputRefs={inputRefs} testIdPrefix="reset" />
              <Button onClick={handleVerifyCode} disabled={codeDigits.join('').length !== 6} className="w-full" data-testid="verify-reset-code-button">
                Verify Code
              </Button>
            </>
          )}

          {step === 'newpass' && (
            <>
              <div className="space-y-2">
                <Label>New Password</Label>
                <Input data-testid="new-password-input" type="password" placeholder="••••••••"
                  value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>Confirm New Password</Label>
                <Input data-testid="confirm-new-password-input" type="password" placeholder="••••••••"
                  value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
              </div>
              <Button onClick={handleReset} disabled={isLoading} className="w-full" data-testid="reset-password-button">
                {isLoading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Resetting...</> : 'Reset Password'}
              </Button>
            </>
          )}

          {step === 'done' && (
            <Button onClick={onExit} className="w-full" data-testid="back-to-login-button">Back to Login</Button>
          )}

          {step !== 'done' && (
            <button onClick={onExit} className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1 mx-auto"
              data-testid="cancel-reset"><ArrowLeft className="w-4 h-4" /> Back to login</button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Login Form ───────────────────────────────────────
function LoginForm({ form, setForm, onSubmit, onForgot, isLoading, t }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="login-email">{t('email')}</Label>
        <Input id="login-email" data-testid="login-email-input" type="email" placeholder="you@example.com"
          value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="login-password">{t('password')}</Label>
        <Input id="login-password" data-testid="login-password-input" type="password" placeholder="••••••••"
          value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
      </div>
      <Button type="submit" data-testid="login-submit-button" className="w-full btn-lift" disabled={isLoading}>
        {isLoading ? t('auth_signing_in') : t('sign_in')}
      </Button>
      <button type="button" onClick={onForgot} className="text-sm text-primary hover:underline w-full text-center mt-2" data-testid="forgot-password-link">
        Forgot password?
      </button>
    </form>
  );
}

// ─── Register Form ────────────────────────────────────
function RegisterForm({ form, setForm, onSubmit, isLoading, t }) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="register-name">{t('full_name')}</Label>
        <Input id="register-name" data-testid="register-name-input" type="text" placeholder="John Doe"
          value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="register-email">{t('email')}</Label>
        <Input id="register-email" data-testid="register-email-input" type="email" placeholder="you@example.com"
          value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="register-password">{t('password')}</Label>
        <Input id="register-password" data-testid="register-password-input" type="password" placeholder="••••••••"
          value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="register-confirm">{t('confirm_password')}</Label>
        <Input id="register-confirm" data-testid="register-confirm-input" type="password" placeholder="••••••••"
          value={form.confirmPassword} onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })} required />
      </div>
      <Button type="submit" data-testid="register-submit-button" className="w-full btn-lift" disabled={isLoading}>
        {isLoading ? t('auth_creating') : t('create_account')}
      </Button>
    </form>
  );
}

// ─── Main AuthPage ────────────────────────────────────
export default function AuthPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, register, loginWithGoogle, verifyEmail, resendCode } = useAuth();
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [showVerification, setShowVerification] = useState(false);
  const [verificationEmail, setVerificationEmail] = useState('');
  const [demoCode, setDemoCode] = useState('');

  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ name: '', email: '', password: '', confirmPassword: '' });

  const [showResetFlow, setShowResetFlow] = useState(false);

  // ─── Auth handlers ───
  const handleLogin = async (e) => {
    e.preventDefault();
    setError(''); setIsLoading(true);
    try {
      const result = await login(loginForm.email, loginForm.password);
      if (result.requires_verification) {
        setVerificationEmail(result.email); setDemoCode(result.demo_code); setShowVerification(true);
      } else { navigate('/dashboard'); }
    } catch (err) { setError(err.message); }
    finally { setIsLoading(false); }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');
    if (registerForm.password !== registerForm.confirmPassword) { setError('Passwords do not match'); return; }
    setIsLoading(true);
    try {
      const result = await register(registerForm.name, registerForm.email, registerForm.password);
      if (result.requires_verification) {
        setVerificationEmail(result.email); setDemoCode(result.demo_code); setShowVerification(true);
      }
    } catch (err) { setError(err.message); }
    finally { setIsLoading(false); }
  };

  const handleVerifyCode = async (code) => {
    setIsLoading(true); setError('');
    try { await verifyEmail(verificationEmail, code); navigate('/dashboard'); return true; }
    catch (err) { setError(err.message); return false; }
    finally { setIsLoading(false); }
  };

  const handleResendCode = async () => {
    setError('');
    try { const r = await resendCode(verificationEmail); setDemoCode(r.demo_code); }
    catch (err) { setError(err.message); }
  };

  const handleRequestResetCode = async (email) => {
    setIsLoading(true); setError('');
    try {
      const res = await fetch(`${API}/auth/forgot-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      return data;
    } catch (err) { setError(err.message); return null; }
    finally { setIsLoading(false); }
  };

  const handleResetPassword = async (email, code, newPassword) => {
    setIsLoading(true); setError('');
    try {
      const res = await fetch(`${API}/auth/reset-password`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code, new_password: newPassword })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      return true;
    } catch (err) { setError(err.message); return false; }
    finally { setIsLoading(false); }
  };

  const exitReset = () => { setShowResetFlow(false); setError(''); };

  // ─── Screen routing ───
  if (showVerification) {
    return <VerificationScreen email={verificationEmail} demoCode={demoCode} error={error}
      isLoading={isLoading} onVerify={handleVerifyCode} onResend={handleResendCode}
      onBack={() => { setShowVerification(false); setError(''); }} />;
  }

  if (showResetFlow) {
    return <PasswordResetFlow error={error} isLoading={isLoading} initialEmail={loginForm.email}
      onRequestCode={handleRequestResetCode} onResetPassword={handleResetPassword}
      onExit={exitReset} setError={setError} />;
  }

  return (
    <div className="min-h-screen flex bg-background">
      {/* Left: Auth Form */}
      <div className="w-full lg:w-[45%] flex items-center justify-center p-6 sm:p-10 relative">
        <div className="absolute top-5 right-5 z-10"><LanguagePicker /></div>
        <div className="w-full max-w-[420px] space-y-8 animate-fade-in">
          <div className="space-y-2">
            <h1 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight">FlowVise</h1>
            <p className="text-muted-foreground text-sm">{t('app_tagline')}</p>
          </div>

          <div className="space-y-6">
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6 bg-muted/50">
                <TabsTrigger value="login" data-testid="login-tab" className="data-[state=active]:bg-card">{t('sign_in')}</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab" className="data-[state=active]:bg-card">{t('create_account')}</TabsTrigger>
              </TabsList>

              <AuthError message={error} />
              {error && <div className="mb-4" />}

              <TabsContent value="login">
                <LoginForm form={loginForm} setForm={setLoginForm} onSubmit={handleLogin}
                  onForgot={() => { setShowResetFlow(true); setError(''); }} isLoading={isLoading} t={t} />
              </TabsContent>

              <TabsContent value="register">
                <RegisterForm form={registerForm} setForm={setRegisterForm}
                  onSubmit={handleRegister} isLoading={isLoading} t={t} />
              </TabsContent>

              <div className="relative my-6">
                <Separator />
                <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-3 text-xs text-muted-foreground">
                  {t('or_continue_with')}
                </span>
              </div>

              <Button type="button" variant="outline" data-testid="google-login-button"
                className="w-full h-11" onClick={loginWithGoogle}>
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                  <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                {t('continue_with_google')}
              </Button>
            </Tabs>
          </div>
        </div>
      </div>

      {/* Right: Visual Panel */}
      <div className="hidden lg:flex lg:w-[55%] relative overflow-hidden items-center justify-center">
        {/* Gradient mesh background */}
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-purple-500/10" />
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-primary/10 rounded-full blur-[120px] -translate-y-1/2 translate-x-1/4" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-emerald-500/8 rounded-full blur-[100px] translate-y-1/3 -translate-x-1/4" />
        <div className="absolute top-1/2 left-1/2 w-[300px] h-[300px] bg-violet-500/5 rounded-full blur-[80px] -translate-x-1/2 -translate-y-1/2" />

        {/* Content */}
        <div className="relative z-10 max-w-lg px-12 space-y-10">
          {/* Feature highlights */}
          <div className="space-y-6">
            <div className="flex items-start gap-4 p-4 rounded-xl bg-card/40 backdrop-blur-sm border border-border/50">
              <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">Smart Risk Analysis</p>
                <p className="text-xs text-muted-foreground mt-0.5">AI-powered spending volatility index tells you exactly when it's safe to invest</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 rounded-xl bg-card/40 backdrop-blur-sm border border-border/50">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                <Shield className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className="font-medium text-sm">Elastic Safety Buffer</p>
                <p className="text-xs text-muted-foreground mt-0.5">Dynamic protection that adapts to your spending patterns — never invest more than you can afford</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 rounded-xl bg-card/40 backdrop-blur-sm border border-border/50">
              <div className="w-10 h-10 rounded-lg bg-violet-500/20 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-violet-400" />
              </div>
              <div>
                <p className="font-medium text-sm">EU Open Banking</p>
                <p className="text-xs text-muted-foreground mt-0.5">Connect to 3,400+ European banks via Tink. Auto-detect income, subscriptions, and patterns.</p>
              </div>
            </div>
          </div>

          {/* Quote */}
          <div className="p-6 bg-card/60 backdrop-blur-xl border border-border/50 rounded-2xl">
            <blockquote className="space-y-3">
              <p className="text-base font-medium leading-relaxed italic">"{t('auth_quote')}"</p>
              <footer className="text-sm text-muted-foreground">— {t('auth_quote_author')}</footer>
            </blockquote>
          </div>
        </div>
      </div>
    </div>
  );
}
