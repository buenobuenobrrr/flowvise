import { Input } from './ui/input';
import { AlertCircle } from 'lucide-react';

/**
 * Reusable 6-digit OTP code input with auto-advance and paste support.
 */
export function CodeInput({ digits, onChange, onKeyDown, inputRefs, testIdPrefix = 'code' }) {
  const handleChange = (index, value) => {
    if (value.length > 1) {
      const parsed = value.replace(/\D/g, '').slice(0, 6).split('');
      const next = [...digits];
      parsed.forEach((d, i) => { if (index + i < 6) next[index + i] = d; });
      onChange(next);
      inputRefs.current[Math.min(index + parsed.length, 5)]?.focus();
      return;
    }
    if (!/^\d?$/.test(value)) return;
    const next = [...digits];
    next[index] = value;
    onChange(next);
    if (value && index < 5) inputRefs.current[index + 1]?.focus();
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    if (onKeyDown) onKeyDown(index, e);
  };

  return (
    <div className="flex justify-center gap-2" data-testid={`${testIdPrefix}-input-group`}>
      {digits.map((digit, index) => (
        <Input
          key={`${testIdPrefix}-${index}`}
          ref={(el) => (inputRefs.current[index] = el)}
          type="text"
          inputMode="numeric"
          maxLength={6}
          value={digit}
          onChange={(e) => handleChange(index, e.target.value)}
          onKeyDown={(e) => handleKeyDown(index, e)}
          className="w-12 h-14 text-center text-xl font-mono font-semibold"
          data-testid={`${testIdPrefix}-digit-${index}`}
        />
      ))}
    </div>
  );
}

export function AuthError({ message }) {
  if (!message) return null;
  return (
    <div className="flex items-center gap-2 p-3 text-sm text-destructive bg-destructive/10 rounded-md">
      <AlertCircle className="w-4 h-4 flex-shrink-0" />
      {message}
    </div>
  );
}

export function DemoCodeBanner({ code, testId = 'demo-code-display' }) {
  if (!code) return null;
  return (
    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-center">
      <p className="text-xs text-amber-600 mb-1">Demo: In production, this code would be emailed</p>
      <p className="text-2xl font-mono font-bold text-amber-800 tracking-[0.3em]" data-testid={testId}>
        {code}
      </p>
    </div>
  );
}
