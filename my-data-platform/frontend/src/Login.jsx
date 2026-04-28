import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

export default function Login() {
  const { login, register, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('viewer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const normalizedUsername = username.trim();
      if (mode === 'register') {
        if (password !== confirmPassword) {
          throw new Error('Passwords do not match.');
        }
        await register(normalizedUsername, password, role);
      } else {
        await login(normalizedUsername, password);
      }
      navigate('/', { replace: true });
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || (mode === 'login' ? 'Login failed.' : 'Registration failed.'));
    } finally {
      setLoading(false);
    }
  };

  const useDemoRole = (role) => {
    if (role === 'admin') {
      setUsername('admin_user');
    } else if (role === 'analyst') {
      setUsername('data_analyst');
    } else {
      setUsername('guest_viewer');
    }
    setPassword('password123');
  };

  return (
    <div className="login-page">
      <div className="login-shell">
        <section className="login-hero">
          <p className="login-kicker">No-Code Big Data Platform</p>
          <h1>Operate your full analytics lifecycle from one workspace.</h1>
          <p>
            Upload, profile, clean, predict, explain, and export with enterprise-ready access control.
          </p>
          <ul>
            <li>Fast upload and schema understanding</li>
            <li>Automated cleaning with audit tracking</li>
            <li>AutoML, NLP, explainability, and workflows</li>
          </ul>
        </section>

        <form className="login-card" onSubmit={onSubmit}>
          <h2>{mode === 'login' ? 'Sign in to DataSaaS Pro' : 'Create secure account'}</h2>
          <p>
            {mode === 'login'
              ? 'Use your role-based account credentials.'
              : 'Register with a strong password and assigned role.'}
          </p>

          <div className="demo-role-row">
            <button type="button" onClick={() => setMode('login')} className={mode === 'login' ? 'active' : ''}>
              Login
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={mode === 'register' ? 'active' : ''}
            >
              Register
            </button>
          </div>

          {mode === 'login' ? (
            <div className="demo-role-row">
              <button type="button" onClick={() => useDemoRole('admin')}>
                Admin
              </button>
              <button type="button" onClick={() => useDemoRole('analyst')}>
                Analyst
              </button>
              <button type="button" onClick={() => useDemoRole('viewer')}>
                Viewer
              </button>
            </div>
          ) : null}

          <label htmlFor="username">Username</label>
          <input
            id="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder="admin_user / data_analyst / guest_viewer"
            autoComplete="username"
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={mode === 'login' ? 'password123' : 'Use strong password'}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
          />

          {mode === 'register' ? (
            <>
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Re-enter password"
                autoComplete="new-password"
                required
              />

              <label htmlFor="role">Role</label>
              <select id="role" value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="viewer">Viewer</option>
                <option value="analyst">Analyst</option>
              </select>

              <small>
                Password must include uppercase, lowercase, number, special character, and be at least 8 chars.
              </small>
            </>
          ) : null}

          {error ? <p className="error">{error}</p> : null}
          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? (mode === 'login' ? 'Signing in...' : 'Creating account...') : mode === 'login' ? 'Sign In' : 'Register'}
          </button>

          {user?.role ? <small>Current role: {user.role}</small> : null}
        </form>
      </div>
    </div>
  );
}
