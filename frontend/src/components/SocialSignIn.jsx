import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { Button } from './ui/button';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const GOOGLE_SCRIPT = 'https://accounts.google.com/gsi/client';
const APPLE_SCRIPT = 'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js';

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) {
      if (existing.getAttribute('data-loaded') === 'true') {
        resolve();
        return;
      }
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('Script failed')), { once: true });
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.onload = () => {
      script.setAttribute('data-loaded', 'true');
      resolve();
    };
    script.onerror = () => reject(new Error('Script failed'));
    document.head.appendChild(script);
  });
}

export function SocialSignIn({ disabled, onError, onSuccess }) {
  const { loginWithIdToken } = useAuth();
  const { t } = useLanguage();
  const googleHost = useRef(null);
  const [providers, setProviders] = useState({ google_client_id: null, apple_client_id: null });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/auth/providers`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        if (!cancelled) setProviders({
          google_client_id: data.google_client_id || null,
          apple_client_id: data.apple_client_id || null,
        });
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const clientId = providers.google_client_id;
    const host = googleHost.current;
    if (!clientId || !host) return undefined;
    let cancelled = false;
    loadScript(GOOGLE_SCRIPT).then(() => {
      if (cancelled || !window.google?.accounts?.id) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          try {
            setBusy(true);
            onError('');
            await loginWithIdToken('auth/google', response.credential);
            onSuccess();
          } catch (err) {
            onError(err.message || 'Google sign-in failed');
          } finally {
            setBusy(false);
          }
        },
      });
      host.innerHTML = '';
      window.google.accounts.id.renderButton(host, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        width: host.offsetWidth || 360,
        logo_alignment: 'left',
      });
    }).catch(() => onError('Google sign-in could not load'));
    return () => { cancelled = true; };
  }, [providers.google_client_id, loginWithIdToken, onError, onSuccess]);

  const startApple = async () => {
    if (!providers.apple_client_id) {
      onError('Apple sign-in is not configured on this server');
      return;
    }
    try {
      setBusy(true);
      onError('');
      await loadScript(APPLE_SCRIPT);
      window.AppleID.auth.init({
        clientId: providers.apple_client_id,
        scope: 'name email',
        redirectURI: `${window.location.origin}/auth`,
        usePopup: true,
      });
      const result = await window.AppleID.auth.signIn();
      const given = result.user?.name;
      const name = given ? [given.firstName, given.lastName].filter(Boolean).join(' ') : '';
      await loginWithIdToken('auth/apple', result.authorization.id_token, name);
      onSuccess();
    } catch (err) {
      if (err?.error !== 'popup_closed_by_user') {
        onError(err.message || 'Apple sign-in failed');
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative my-2">
        <div className="h-px bg-border" />
        <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-3 text-xs text-muted-foreground">
          {t('or_continue_with')}
        </span>
      </div>
      {providers.google_client_id ? (
        <div ref={googleHost} className="min-h-11 w-full overflow-hidden" data-testid="google-login-button" />
      ) : (
        <Button
          type="button"
          variant="outline"
          className="w-full h-11"
          disabled={disabled || busy}
          data-testid="google-login-button"
          onClick={() => onError('Google sign-in is not configured on this server')}
        >
          {t('continue_with_google')}
        </Button>
      )}
      <Button
        type="button"
        variant="outline"
        className="w-full h-11"
        disabled={disabled || busy}
        data-testid="apple-login-button"
        onClick={startApple}
      >
        {t('continue_with_apple')}
      </Button>
    </div>
  );
}
