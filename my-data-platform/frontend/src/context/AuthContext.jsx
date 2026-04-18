import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const STORAGE_KEY = 'my_data_platform_auth';

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
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
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
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }, [user]);

  const login = async (username, password) => {
    const body = new URLSearchParams();
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
    };

    applyAuthHeader(userData.token);
    setUser(userData);
    return userData;
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
