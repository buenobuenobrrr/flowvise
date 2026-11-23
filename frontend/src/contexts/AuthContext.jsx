import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

const AuthContext = createContext(null);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const HTTP_FORBIDDEN = 403;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    if (window.location.hash?.includes('session_id=')) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API}/auth/me`, {
        credentials: 'include'
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        setUser(null);
      }
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email, password) => {
    const response = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    if (response.status === HTTP_FORBIDDEN && data.requires_verification) {
      // User needs to verify email
      return { requires_verification: true, email: data.email, demo_code: data.demo_code };
    }

    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    setUser(data.user);
    return { user: data.user };
  }, []);

  const register = useCallback(async (name, email, password) => {
    const response = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, email, password })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed');
    }

    // Registration now returns verification requirement
    return {
      requires_verification: true,
      email: data.email,
      demo_code: data.demo_code
    };
  }, []);

  const verifyEmail = useCallback(async (email, code) => {
    const response = await fetch(`${API}/auth/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, code })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Verification failed');
    }

    setUser(data.user);
    return data.user;
  }, []);

  const resendCode = useCallback(async (email) => {
    const response = await fetch(`${API}/auth/resend-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to resend code');
    }

    return data;
  }, []);

  const loginWithGoogle = useCallback(() => {
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  }, []);

  const processGoogleCallback = useCallback(async (sessionId) => {
    const response = await fetch(`${API}/auth/google/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ session_id: sessionId })
    });

    if (!response.ok) {
      throw new Error('Google auth failed');
    }

    const data = await response.json();
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Logout request failed:', err);
    }
    setUser(null);
  }, []);

  const getAuthHeaders = useCallback(() => {
    return { 'Content-Type': 'application/json' };
  }, []);

  // All deps are stable useCallback references — the large array is intentional
  const value = useMemo(() => ({
    user,
    loading,
    login,
    register,
    verifyEmail,
    resendCode,
    loginWithGoogle,
    processGoogleCallback,
    logout,
    getAuthHeaders,
    checkAuth
  }), [user, loading, login, register, verifyEmail, resendCode, loginWithGoogle, processGoogleCallback, logout, getAuthHeaders, checkAuth]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
