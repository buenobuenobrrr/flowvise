import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { LanguagePicker } from '../components/LanguagePicker';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { FlowMark } from '../components/FlowMark';
import { TrendingUp, Shield, ArrowLeft, Mail, Loader2, KeyRound, Sparkles } from 'lucide-react';
import { CodeInput, AuthError, DemoCodeBanner } from '../components/AuthComponents';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
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
  const { login, register, verifyEmail, resendCode } = useAuth();
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
      <div className="w-full lg:w-[480px] lg:shrink-0 flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-[440px] space-y-8 animate-fade-in bg-card border border-border shadow-card rounded-xl p-8 sm:p-10">
          <div className="flex justify-end -mt-2 -mr-2"><LanguagePicker /></div>
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <FlowMark className="w-10 h-10" />
              <h1 className="font-heading text-3xl sm:text-4xl font-medium tracking-tight">FlowVise</h1>
            </div>
            <p className="text-muted-foreground">{t('app_tagline')}</p>
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

            </Tabs>
          </div>
        </div>
      </div>

      {/* Right: Visual Panel */}
      <div className="hidden lg:flex flex-1 min-w-0 relative overflow-hidden items-center justify-center auth-panel">
        <div className="relative z-10 max-w-md px-10 space-y-4">
          <div className="space-y-3">
            <div className="flex items-start gap-4 p-5 rounded-xl bg-card text-card-foreground border border-white/10">
              <div className="w-10 h-10 rounded-md bg-secondary flex items-center justify-center flex-shrink-0">
                <TrendingUp className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">Smart Risk Analysis</p>
                <p className="text-sm text-muted-foreground mt-1">AI-powered spending volatility index tells you exactly when it's safe to invest</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-5 rounded-xl bg-card text-card-foreground border border-white/10">
              <div className="w-10 h-10 rounded-md bg-secondary flex items-center justify-center flex-shrink-0">
                <Shield className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">Elastic Safety Buffer</p>
                <p className="text-sm text-muted-foreground mt-1">Dynamic protection that adapts to your spending patterns — never invest more than you can afford</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-5 rounded-xl bg-card text-card-foreground border border-white/10">
              <div className="w-10 h-10 rounded-md bg-secondary flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="font-medium text-sm">EU Open Banking</p>
                <p className="text-sm text-muted-foreground mt-1">Connect to 3,400+ European banks via Tink. Auto-detect income, subscriptions, and patterns.</p>
              </div>
            </div>
          </div>

          <div className="p-6 bg-card text-card-foreground border border-white/10 rounded-xl">
            <blockquote className="space-y-3">
              <p className="text-base leading-relaxed">"{t('auth_quote')}"</p>
              <footer className="text-sm text-muted-foreground">— {t('auth_quote_author')}</footer>
            </blockquote>
          </div>
        </div>
      </div>
    </div>
  );
}
