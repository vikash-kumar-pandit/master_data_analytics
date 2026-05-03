import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { getAxiosErrorMessage } from './utils/errorHandler';

const USERNAME_PATTERN = /^[a-z0-9_.-]{3,64}$/;
const EMAIL_PATTERN = /^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,63}$/i;

function validatePasswordStrength(password) {
  if (password.length < 8) {
    return 'Password must be at least 8 characters.';
  }
  if (!/[A-Z]/.test(password)) {
    return 'Password must contain an uppercase letter.';
  }
  if (!/[a-z]/.test(password)) {
    return 'Password must contain a lowercase letter.';
  }
  if (!/\d/.test(password)) {
    return 'Password must contain a number.';
  }
  if (!/[^A-Za-z0-9]/.test(password)) {
    return 'Password must contain a special character.';
  }
  return '';
}

export default function Login() {
  const {
    login,
    registerWithEmail,
    verifyEmail,
    resendVerification,
    requestPasswordReset,
    confirmPasswordReset,
    isAuthenticated,
    user,
  } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState('login');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('viewer');
  const [resetToken, setResetToken] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const verifyToken = params.get('verify_token');
    const incomingResetToken = params.get('reset_token');

    if (incomingResetToken) {
      setMode('reset');
      setResetToken(incomingResetToken);
      setMessage('Reset token detected. Please set your new password.');
      return;
    }

    if (!verifyToken) {
      return;
    }

    let cancelled = false;
    const runVerification = async () => {
      try {
        const response = await verifyEmail(verifyToken);
        if (!cancelled) {
          setMode('login');
          setMessage(response?.message || 'Email verified successfully. Please login.');
        }
      } catch (verificationError) {
        if (!cancelled) {
          setError(getAxiosErrorMessage(verificationError, 'Email verification failed.'));
        }
      }
    };

    runVerification();
    return () => {
      cancelled = true;
    };
  }, [location.search, verifyEmail]);

  const onSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setMessage('');
    setLoading(true);

    try {
      const normalizedUsername = username.trim();
      const normalizedEmail = email.trim().toLowerCase();

      if (mode === 'register') {
        if (!USERNAME_PATTERN.test(normalizedUsername.toLowerCase())) {
          throw new Error('Username must be 3-64 characters and use only letters, numbers, underscore, hyphen, or dot.');
        }
        if (!EMAIL_PATTERN.test(normalizedEmail)) {
          throw new Error('Please enter a valid email address.');
        }
        const passwordError = validatePasswordStrength(password);
        if (passwordError) {
          throw new Error(passwordError);
        }
        if (password !== confirmPassword) {
          throw new Error('Passwords do not match.');
        }
        const response = await registerWithEmail(normalizedUsername, normalizedEmail, password, role);
        setMessage(response?.message || 'Registration complete. Check your email to verify your account.');
        if (response?.verification_token) {
          setMessage(
            `${response?.message || 'Registration complete.'} Dev token: ${response.verification_token}`
          );
        }
        setMode('login');
      } else if (mode === 'forgot') {
        const response = await requestPasswordReset(normalizedEmail);
        setMessage(response?.message || 'If account exists, reset link sent.');
        if (response?.reset_token) {
          setMessage(`${response?.message || ''} Dev token: ${response.reset_token}`.trim());
        }
      } else if (mode === 'reset') {
        if (password !== confirmPassword) {
          throw new Error('Passwords do not match.');
        }
        const response = await confirmPasswordReset(resetToken, password);
        setMessage(response?.message || 'Password reset successful. Please login.');
        setMode('login');
        setPassword('');
        setConfirmPassword('');
      } else if (mode === 'resend') {
        const response = await resendVerification(normalizedEmail);
        setMessage(response?.message || 'Verification email sent.');
        if (response?.verification_token) {
          setMessage(`${response?.message || ''} Dev token: ${response.verification_token}`.trim());
        }
      } else {
        await login(normalizedUsername, password);
        navigate('/', { replace: true });
      }
    } catch (requestError) {
      const fallback = mode === 'login' ? 'Login failed.' : 'Authentication request failed.';
      const responseStatus = requestError?.response?.status;
      const messageText = getAxiosErrorMessage(requestError, fallback);

      if (responseStatus === 403 && mode === 'login') {
        setError(`${messageText} Use Resend Verify if you need a new verification link.`);
        return;
      }

      setError(messageText);
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
            <button type="button" onClick={() => setMode('forgot')} className={mode === 'forgot' ? 'active' : ''}>
              Forgot
            </button>
            <button type="button" onClick={() => setMode('resend')} className={mode === 'resend' ? 'active' : ''}>
              Resend Verify
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

          {mode === 'login' || mode === 'register' ? (
            <>
              <label htmlFor="username">Username</label>
              <input
                id="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="admin_user / data_analyst / guest_viewer"
                autoComplete="username"
                required
              />
            </>
          ) : null}

          {mode === 'register' || mode === 'forgot' || mode === 'resend' ? (
            <>
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="name@company.com"
                autoComplete="email"
                required
              />
            </>
          ) : null}

          {mode === 'login' || mode === 'register' || mode === 'reset' ? (
            <>
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
            </>
          ) : null}

          {mode === 'register' || mode === 'reset' ? (
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

              {mode === 'register' ? (
                <>
                  <label htmlFor="role">Role</label>
                  <select id="role" value={role} onChange={(event) => setRole(event.target.value)}>
                    <option value="viewer">Viewer</option>
                    <option value="analyst">Analyst</option>
                  </select>
                </>
              ) : null}

              <small>
                Password must include uppercase, lowercase, number, special character, and be at least 8 chars.
              </small>
            </>
          ) : null}

          {mode === 'reset' ? (
            <>
              <label htmlFor="resetToken">Reset Token</label>
              <input
                id="resetToken"
                value={resetToken}
                onChange={(event) => setResetToken(event.target.value)}
                placeholder="Paste reset token"
                required
              />
            </>
          ) : null}

          {message ? <p className="success">{message}</p> : null}
          {error ? <p className="error">{error}</p> : null}
          <button type="submit" className="login-submit" disabled={loading}>
            {loading
              ? 'Processing...'
              : mode === 'login'
              ? 'Sign In'
              : mode === 'register'
              ? 'Register'
              : mode === 'forgot'
              ? 'Send Reset Link'
              : mode === 'resend'
              ? 'Resend Verification'
              : 'Reset Password'}
          </button>

          {user?.role ? <small>Current role: {user.role}</small> : null}
        </form>
      </div>
    </div>
  );
}
