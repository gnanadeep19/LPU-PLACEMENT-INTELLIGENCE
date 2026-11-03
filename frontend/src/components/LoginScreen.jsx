import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, Eye, EyeOff, Info } from 'lucide-react';
import { BrandLogo } from './ui';
import campusImage from '../assets/lpu-campus-banner.webp';
import { usesSupabaseAuth } from '../services/supabaseClient';

export default function LoginScreen({ onLogin, message, busy }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const isBusy = busy || submitting;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isBusy) return;
    if (!username.trim() || !password) {
      setError(`Enter both your ${usesSupabaseAuth ? 'email' : 'username'} and password.`);
      return;
    }
    setError('');
    setSubmitting(true);
    try {
      const failure = await onLogin(username.trim(), password);
      if (failure) {
        setError(failure);
      } else {
        setPassword('');
        setShowPassword(false);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-shell">
      <a className="skip-link" href="#login-form">
        Skip to sign-in form
      </a>

      <main className="login-main login-layout">
        <section className="login-hero" aria-labelledby="login-hero-heading">
          <div className="login-hero-content">
            <div className="login-brand">
              <BrandLogo />
              <div>
                <h1>LPU Placement Intelligence</h1>
                <p>Student readiness platform</p>
              </div>
            </div>
            <div className="login-hero-message">
              <span className="login-eyebrow"><span aria-hidden="true" /> YOUR NEXT CHAPTER STARTS HERE</span>
              <h2 id="login-hero-heading">Your future,<br /><em>in focus.</em></h2>
              <p>Build on your strengths, make a plan, and move towards your goals with confidence.</p>
            </div>
            <div className="login-campus-frame">
              <img className="login-hero-image" src={campusImage} alt="LPU campus building with the university logo" />
              <div className="login-campus-label"><span>MADE FOR YOUR JOURNEY</span><strong>From preparation to opportunity.</strong></div>
            </div>
            <div className="login-hero-footer"><span>STUDENT PROJECT DEMO</span><span>LPU campus · Image from Distance Education School</span></div>
          </div>
        </section>

        <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-panel-top"><span>YOUR WORKSPACE</span><span className="login-panel-top-mark" aria-hidden="true">✳</span></div>
        <div className="glass-card login-card">
          <span className="login-welcome">WELCOME BACK <span aria-hidden="true">/</span> SIGN IN</span>
          <h2 id="login-heading">Sign in</h2>
          <p className="login-intro">
            Your next step starts here. Sign in to continue to your workspace.
          </p>

          {message ? (
            <div className="status-banner status-banner-warning" role="status">
              <Info size={16} aria-hidden="true" />
              <span>{message}</span>
            </div>
          ) : null}

          <form
            id="login-form"
            className="login-form"
            onSubmit={handleSubmit}
            noValidate
            tabIndex="-1"
          >
            {error ? (
              <div className="form-validation-message" role="alert">
                <AlertTriangle size={16} aria-hidden="true" />
                {error}
              </div>
            ) : null}

            <div className="login-field">
              <label htmlFor="login-username">{usesSupabaseAuth ? 'Email' : 'Username'}</label>
              <input
                id="login-username"
                name="username"
                type={usesSupabaseAuth ? 'email' : 'text'}
                autoComplete="username"
                autoCapitalize="none"
                spellCheck="false"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                disabled={isBusy}
                required
              />
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Password</label>
              <div className="login-password-wrapper">
              <input
                id="login-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={isBusy}
                required
              />
              <button type="button" className="login-password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} title={showPassword ? 'Hide password' : 'Show password'} disabled={isBusy} onClick={() => setShowPassword((visible) => !visible)}>
                {showPassword ? <EyeOff size={19} aria-hidden="true" /> : <Eye size={19} aria-hidden="true" />}
              </button>
              </div>
            </div>

            <button type="submit" className="btn-submit" disabled={isBusy} aria-busy={isBusy}>
              {isBusy ? (
                'Signing in...'
              ) : (
                <>
                  Sign in
                  <ArrowRight size={18} aria-hidden="true" />
                </>
              )}
            </button>
          </form>

          <p className="login-note">
            Need an account? Contact your project administrator.
          </p>
        </div>
        <p className="login-panel-footer"><span>STUDENT · MENTOR · ADMIN</span><span>PLACEMENT INTELLIGENCE</span></p>
        </section>
      </main>
    </div>
  );
}
