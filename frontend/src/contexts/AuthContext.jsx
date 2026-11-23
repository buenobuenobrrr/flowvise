import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';

const AuthContext = createContext(null);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const HTTP_FORBIDDEN = 403;
const TOKEN_KEY = 'flowwise_access_token';

function persistToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function readToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const getAuthHeaders = useCallback(() => {
    const headers = { 'Content-Type': 'application/json' };
    const token = readToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  }, []);

  const checkAuth = useCallback(async () => {
    if (window.location.hash?.includes('session_id=')) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API}/auth/me`, {
        credentials: 'include',
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        setUser(null);
        persistToken(null);
      }
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

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
      return { requires_verification: true, email: data.email, demo_code: data.demo_code };
    }

    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }

    persistToken(data.access_token);
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

    persistToken(data.access_token);
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
    persistToken(data.access_token || data.session_token || null);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
        headers: getAuthHeaders(),
      });
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Logout request failed:', err);
    }
    persistToken(null);
    setUser(null);
  }, [getAuthHeaders]);

  const value = useMemo(() => ({
    user,
    loading,
    login,
    register,
    verifyEmail,
    resendCode,
    processGoogleCallback,
    logout,
    getAuthHeaders,
    checkAuth
  }), [user, loading, login, register, verifyEmail, resendCode, processGoogleCallback, logout, getAuthHeaders, checkAuth]);

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
