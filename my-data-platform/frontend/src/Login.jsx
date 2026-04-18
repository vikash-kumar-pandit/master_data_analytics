import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';

export default function Login() {
  const { login, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
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
      await login(username.trim(), password);
      navigate('/', { replace: true });
    } catch (requestError) {
      setError(requestError?.response?.data?.detail || 'Login failed.');
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
          <h2>Sign in to DataSaaS Pro</h2>
          <p>Use your role-based account credentials.</p>

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
            placeholder="password123"
            autoComplete="current-password"
            required
          />

          {error ? <p className="error">{error}</p> : null}
          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>

          {user?.role ? <small>Current role: {user.role}</small> : null}
        </form>
      </div>
    </div>
  );
}
