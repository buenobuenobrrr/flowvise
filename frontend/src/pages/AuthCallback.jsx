import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const navigate = useNavigate();
  const { processGoogleCallback } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Use useRef to prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processSession = async () => {
      try {
        const hash = window.location.hash;
        const params = new URLSearchParams(hash.replace('#', ''));
        const sessionId = params.get('session_id');

        if (!sessionId) {
          navigate('/auth');
          return;
        }

        // Exchange session_id for a real session — retry once on failure.
        try {
          await processGoogleCallback(sessionId);
        } catch (firstErr) {
          // Race condition with cookie propagation — retry once after a short wait.
          if (process.env.NODE_ENV !== 'production') console.debug('Google callback retry:', firstErr);
          await new Promise(r => setTimeout(r, 1000));
          await processGoogleCallback(sessionId);
        }

        window.history.replaceState(null, '', window.location.pathname);
        navigate('/dashboard', { replace: true });
      } catch (err) {
        navigate('/auth');
      }
    };

    processSession();
  }, [navigate, processGoogleCallback]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4">
        <Loader2 className="w-10 h-10 animate-spin mx-auto text-primary" />
        <p className="text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  );
}
