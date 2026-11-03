import React from 'react';
import Dashboard from './app/Dashboard';
import LoginScreen from './components/LoginScreen';
import { BrandLogo } from './components/ui';
import { useAuth } from './hooks/useAuth';

function SessionSplash() {
  return (
    <div className="login-shell">
      <main className="login-main">
        <div className="login-brand">
          <BrandLogo />
          <div>
            <h1>LPU Placement Intelligence</h1>
            <p>Student readiness diagnostics</p>
          </div>
        </div>
        <div className="glass-card login-card" role="status" aria-live="polite">
          <span className="loading-line loading-line-short" />
          <span className="loading-line loading-line-medium" />
          <p className="login-note">Checking your session...</p>
        </div>
      </main>
    </div>
  );
}

export default function App() {
  const { user, status, message, login, logout } = useAuth();

  if (status === 'loading') {
    return <SessionSplash />;
  }

  if (!user) {
    return <LoginScreen onLogin={login} message={message} busy={status === 'authenticating'} />;
  }

  return <Dashboard key={user.id} user={user} onLogout={logout} />;
}
