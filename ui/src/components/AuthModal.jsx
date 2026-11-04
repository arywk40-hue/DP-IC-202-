import React, { useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

export default function AuthModal({ isOpen, onClose }) {
  const { user, loading, error, authConfig, loginWithGoogle, loginDemo, logout } = useAuth();
  const googleBtnRef = useRef(null);

  useEffect(() => {
    if (!isOpen || user || !authConfig?.googleClientId) return undefined;
    let disposed = false;
    const interval = setInterval(() => {
      if (!window.google?.accounts?.id || !googleBtnRef.current || disposed) return;
      clearInterval(interval);
      window.google.accounts.id.initialize({
        client_id: authConfig.googleClientId,
        callback: ({ credential }) => {
          if (credential) loginWithGoogle(credential).then(onClose).catch(() => {});
        },
      });
      window.google.accounts.id.renderButton(googleBtnRef.current, {
        theme: 'outline', size: 'large', width: 280,
        text: 'signin_with', shape: 'rectangular',
      });
    }, 200);
    return () => { disposed = true; clearInterval(interval); };
  }, [isOpen, user, authConfig, loginWithGoogle, onClose]);

  if (!isOpen) return null;

  const handleDemoSignIn = async () => {
    try { await loginDemo(); onClose(); } catch { /* Error is shown below. */ }
  };

  return (
    <div className="auth-modal-overlay" role="dialog" aria-modal="true" aria-label="INDRA sign in" onClick={onClose}>
      <div className="auth-modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="auth-modal-header">
          <div>
            <span className="eyebrow">Identity</span>
            <h3>{user ? (user.provider === 'google' ? 'Google account' : 'Local demo account') : 'Sign in to INDRA'}</h3>
          </div>
          <button type="button" className="auth-modal-close" onClick={onClose} aria-label="Close dialog">&times;</button>
        </div>

        {error && <div className="version-banner" role="alert" style={{ margin: '0 0 1rem' }}>{error}</div>}

        {user ? (
          <>
            <div className="auth-user-card">
              {user.picture ? <img src={user.picture} alt="" className="auth-avatar-large" /> :
                <div className="auth-avatar-placeholder">{user.name?.[0]?.toUpperCase() || 'U'}</div>}
              <div className="auth-user-info">
                <strong>{user.name}</strong><span>{user.email}</span>
                <span className="auth-badge-verified">{user.provider === 'google' ? 'Google identity verified' : 'Local demo identity'}</span>
              </div>
            </div>
            <p className="auth-footer-note">This account displays identity only. Dashboard data is read-only; station control is not connected.</p>
            <div className="auth-modal-actions">
              <button type="button" className="btn-signout" onClick={async () => { await logout(); onClose(); }}>Sign out</button>
              <button type="button" className="heat-toggle" onClick={onClose}>Done</button>
            </div>
          </>
        ) : (
          <>
            <p className="auth-signin-lead">Sign in to view the account attached to this browser session. Signing in does not grant hardware control.</p>
            {authConfig?.googleClientId && <div className="google-btn-wrapper"><div ref={googleBtnRef} /></div>}
            {authConfig?.demoAuthEnabled && <button type="button" className="btn-quick-operator" onClick={handleDemoSignIn} disabled={loading}>
              {loading ? 'Signing in…' : 'Continue with local demo account'}
            </button>}
            {!authConfig?.authEnabled && <p role="status">Sign-in is not configured on this server.</p>}
            <div className="auth-footer-note">{authConfig?.googleClientId ? 'Google identity verification' : authConfig?.demoAuthEnabled ? 'Local demo sign-in' : 'No authentication provider configured'}</div>
          </>
        )}
      </div>
    </div>
  );
}
