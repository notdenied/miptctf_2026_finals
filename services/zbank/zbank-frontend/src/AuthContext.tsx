import React, { createContext, useContext, useState, useEffect } from 'react';
import { fetchApi } from './api';

interface User {
  id: number;
  username: string;
}

interface AuthContextType {
  user: User | null;
  login: (u: string, p: string) => Promise<void>;
  register: (u: string, p: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if logged in by hitting a protected endpoint
    fetchApi('/accounts')
      .then(() => {
        // If it succeeds, we are logged in, but we don't have user info directly.
        // Actually, ZBank login returns user info. We can store it in localStorage.
        const storedUser = localStorage.getItem('zbank_user');
        if (storedUser) setUser(JSON.parse(storedUser));
      })
      .catch(() => {
        setUser(null);
        localStorage.removeItem('zbank_user');
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (u: string, p: string) => {
    const res = await fetchApi('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username: u, password: p })
    });
    setUser(res);
    localStorage.setItem('zbank_user', JSON.stringify(res));
  };

  const register = async (u: string, p: string) => {
    await fetchApi('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username: u, password: p })
    });
    // ZBank api /auth/register does NOT log you in automatically, so let's log in
    await login(u, p);
  };

  const logout = () => {
    // Actually no logout endpoint exists in basic ZBank, but we can clear cookie or just clear state
    // To fully logout from Spring session without endpoint, one would just drop cookie.
    setUser(null);
    localStorage.removeItem('zbank_user');
    window.location.href = '/';
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
