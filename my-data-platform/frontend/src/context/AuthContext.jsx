import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const STORAGE_KEY = 'my_data_platform_auth';
const STORAGE =
  typeof window !== 'undefined'
    ? window.sessionStorage || window.localStorage
    : {
        getItem: () => null,
        setItem: () => {},
        removeItem: () => {},
      };

const AuthContext = createContext(null);

function applyAuthHeader(token) {
  if (token) {
    axios.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete axios.defaults.headers.common.Authorization;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = STORAGE.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      const isExpired = parsed?.expiresAt && Date.now() > parsed.expiresAt;
      if (isExpired) {
        STORAGE.removeItem(STORAGE_KEY);
        applyAuthHeader(null);
        return null;
      }
      applyAuthHeader(parsed?.token || null);
      return parsed;
    } catch {
      applyAuthHeader(null);
      return null;
    }
  });

  useEffect(() => {
    applyAuthHeader(user?.token || null);
    if (user) {
      STORAGE.setItem(STORAGE_KEY, JSON.stringify(user));
    } else {
      STORAGE.removeItem(STORAGE_KEY);
    }
  }, [user]);

  useEffect(() => {
    const interceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401) {
          applyAuthHeader(null);
          setUser(null);
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptor);
    };
  }, []);

  const login = async (username, password) => {
    const body = new URLSearchParams();
    body.append('grant_type', 'password');
    body.append('username', username);
    body.append('password', password);

    const response = await axios.post(`${API_BASE_URL}/api/auth/login`, body, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    const userData = {
      username: response.data.username || username,
      role: response.data.role,
      token: response.data.access_token,
      expiresAt: Date.now() + (response.data.expires_in || 7200) * 1000,
    };

    applyAuthHeader(userData.token);
    setUser(userData);
    return userData;
  };

  const register = async (username, password, role = 'viewer') => {
    throw new Error('Use registerWithEmail instead.');
  };

  const registerWithEmail = async (username, email, password, role = 'viewer') => {
    const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
      username,
      email,
      password,
      role,
    });
    return response.data;
  };

  const verifyEmail = async (token) => {
    const response = await axios.get(`${API_BASE_URL}/api/auth/verify-email`, {
      params: { token },
    });
    return response.data;
  };

  const resendVerification = async (email) => {
    const response = await axios.post(`${API_BASE_URL}/api/auth/resend-verification`, {
      email,
    });
    return response.data;
  };

  const requestPasswordReset = async (email) => {
    const response = await axios.post(`${API_BASE_URL}/api/auth/password-reset/request`, {
      email,
    });
    return response.data;
  };

  const confirmPasswordReset = async (token, newPassword) => {
    const response = await axios.post(`${API_BASE_URL}/api/auth/password-reset/confirm`, {
      token,
      new_password: newPassword,
    });
    return response.data;
  };

  const logout = () => {
    applyAuthHeader(null);
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user?.token),
      login,
      registerWithEmail,
      verifyEmail,
      resendVerification,
      requestPasswordReset,
      confirmPasswordReset,
      register,
      logout,
    }),
    [user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
