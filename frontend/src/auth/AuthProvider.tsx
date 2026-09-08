import React, { createContext, useContext, useState, useEffect } from 'react';

export type UserRole = 'SITE_ENGINEER' | 'SUPERVISOR';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const MOCK_ACCOUNTS: Record<string, { password: string; full_name: string; role: UserRole; id: string }> = {
  'planner@setu.ai': {
    password: 'demo123',
    full_name: 'Rajesh Kumar (Lead Planner)',
    role: 'SUPERVISOR',
    id: 'usr-supervisor-01',
  },
  'engineer@setu.ai': {
    password: 'demo123',
    full_name: 'Vikram Sharma (Site Engineer)',
    role: 'SITE_ENGINEER',
    id: 'usr-engineer-01',
  },
  'supervisor@setu.in': {
    password: 'supervisor123',
    full_name: 'Project Supervisor',
    role: 'SUPERVISOR',
    id: 'usr-supervisor-02',
  },
  'engineer@setu.in': {
    password: 'engineer123',
    full_name: 'Site Engineer',
    role: 'SITE_ENGINEER',
    id: 'usr-engineer-02',
  },
};

const SESSION_KEY = 'setu_session_v1';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as User;
        setUser(parsed);
      }
    } catch {
      localStorage.removeItem(SESSION_KEY);
    } finally {
      setLoading(false);
    }
  }, []);

  const clearError = () => setError(null);

  const login = async (email: string, password: string): Promise<void> => {
    setError(null);
    setLoading(true);

    const emailTrimmed = email.trim().toLowerCase();

    // Latency
    await new Promise((r) => setTimeout(r, 600));

    const account = MOCK_ACCOUNTS[emailTrimmed];

    if (account) {
      if (account.password !== password && password !== 'demo123') {
        setError('Incorrect password. Please try again.');
        setLoading(false);
        throw new Error('Incorrect password.');
      }

      const loggedInUser: User = {
        id: account.id,
        email: emailTrimmed,
        full_name: account.full_name,
        role: account.role,
      };

      setUser(loggedInUser);
      localStorage.setItem(SESSION_KEY, JSON.stringify(loggedInUser));
      setLoading(false);
      return;
    }

    // Default fallback login for any user input
    const isSupervisor = emailTrimmed.includes('planner') || emailTrimmed.includes('supervisor');
    const loggedInUser: User = {
      id: `usr-${Date.now()}`,
      email: emailTrimmed,
      full_name: isSupervisor ? 'Project Supervisor' : 'Field Engineer',
      role: isSupervisor ? 'SUPERVISOR' : 'SITE_ENGINEER',
    };

    setUser(loggedInUser);
    localStorage.setItem(SESSION_KEY, JSON.stringify(loggedInUser));
    setLoading(false);
  };

  const logout = async (): Promise<void> => {
    setUser(null);
    localStorage.removeItem(SESSION_KEY);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        isLoading: loading,
        error,
        login,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
