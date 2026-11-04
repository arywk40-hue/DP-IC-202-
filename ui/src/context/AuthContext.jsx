import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getAuthConfig, authWithGoogle, authDemo, getAuthMe, authLogout } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [authConfig, setAuthConfig] = useState({ googleClientId: '', demoAuthEnabled: false, authEnabled: false });

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('indra_auth_token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await getAuthMe();
      setUser(res.user);
      setError(null);
    } catch {
      localStorage.removeItem('indra_auth_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // 1. Fetch backend auth config
    getAuthConfig()
      .then((cfg) => {
        setAuthConfig(cfg);
        // If Google Client ID is configured, load Google Identity Services SDK script
        if (cfg.googleClientId && !document.getElementById('google-gsi-client')) {
          const script = document.createElement('script');
          script.id = 'google-gsi-client';
          script.src = 'https://accounts.google.com/gsi/client';
          script.async = true;
          script.defer = true;
          document.body.appendChild(script);
        }
      })
      .catch(() => {});

    // 2. Fetch current user session if token exists
    refreshUser();
  }, [refreshUser]);

  const loginWithGoogle = async (credential) => {
    try {
      setLoading(true);
      setError(null);
      const res = await authWithGoogle(credential);
      if (res.token) {
        localStorage.setItem('indra_auth_token', res.token);
        setUser(res.user);
        return res.user;
      }
    } catch (err) {
      setError(err.message || 'Google sign-in failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const loginDemo = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await authDemo();
      if (res.token) {
        localStorage.setItem('indra_auth_token', res.token);
        setUser(res.user);
        return res.user;
      }
    } catch (err) {
      setError(err.message || 'Demo authentication failed');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authLogout();
    } catch {
      // ignore
    } finally {
      localStorage.removeItem('indra_auth_token');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        authConfig,
        loginWithGoogle,
        loginDemo,
        logout,
        refreshUser,
      }}
    >
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
