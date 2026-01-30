'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  id: string;
  email: string;
  company_id: number;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, companyName: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Default user - no auth required
const DEFAULT_USER: User = {
  id: 'default-user',
  email: 'admin@nexai.com',
  company_id: 1
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Auto-login with default user (no auth required)
    setUser(DEFAULT_USER);
    setLoading(false);
  }, []);

  async function signIn(email: string, password: string) {
    // Accept any credentials
    setUser({
      id: 'user-' + Date.now(),
      email: email,
      company_id: 1
    });
  }

  async function signUp(email: string, password: string, companyName: string) {
    // Accept any registration
    setUser({
      id: 'user-' + Date.now(),
      email: email,
      company_id: 1
    });
  }

  async function signOut() {
    // Just redirect, keep default user
    setUser(DEFAULT_USER);
    if (typeof window !== 'undefined') {
      window.location.href = '/dashboard';
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
