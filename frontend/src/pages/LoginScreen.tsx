import React, { useState } from 'react';
import { useAuth } from '@/auth/AuthProvider';
import { useTheme } from '@/theme/ThemeProvider';
import { Navigate, useLocation } from 'react-router-dom';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import {
  Lock,
  Mail,
  Eye,
  EyeOff,
  ShieldCheck,
  HardHat,
  AlertCircle,
  ArrowRight,
  Sun,
  Moon,
  Flame,
  Droplets,
} from 'lucide-react';

// Oil India Limited (OIL) brand
const OIL_BLACK = '#2B2A29';
const OIL_RED = '#E31E24';
const OIL_GRAY = '#6B6A68'; // restrained neutral accent — never a substitute for red/black

export default function LoginScreen() {
  const { login, isAuthenticated, user, error, clearError, isLoading } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [fieldError, setFieldError] = useState('');

  if (isAuthenticated && user) {
    const defaultRoute = user.role === 'SUPERVISOR' ? '/digest' : '/intake';
    const from = (location.state as any)?.from?.pathname || defaultRoute;
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldError('');
    clearError();

    if (!email.trim()) { setFieldError('Please enter your email address.'); return; }
    if (!email.includes('@')) { setFieldError('Please enter a valid email address.'); return; }
    if (!password.trim()) { setFieldError('Please enter your password.'); return; }

    try {
      await login(email.trim(), password);
    } catch (err: any) {
      // Handled in context
    }
  };

  const fillDemo = (demoEmail: string) => {
    setEmail(demoEmail);
    setPassword('Demo123456!');
    setFieldError('');
    clearError();
  };

  return (
    <div
      className="min-h-screen flex font-sans antialiased selection:bg-[#E31E24] selection:text-white transition-colors duration-200 relative overflow-hidden"
      style={{ backgroundColor: theme === 'dark' ? '#1a1918' : '#FFFFFF' }}
    >
      {/* ── LEFT PANEL — Brand panel (hidden on mobile) ────────────────────── */}
      <div
        className="hidden lg:flex lg:w-[45%] flex-col justify-between p-10 relative overflow-hidden"
        style={{ backgroundColor: OIL_BLACK }}
      >
        {/* Background decorative circles */}
        <div
          className="absolute -top-24 -left-24 w-96 h-96 rounded-full opacity-10"
          style={{ backgroundColor: OIL_RED }}
        />
        <div
          className="absolute bottom-0 right-0 w-80 h-80 rounded-full opacity-10"
          style={{ backgroundColor: OIL_GRAY }}
        />
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full opacity-5"
          style={{ backgroundColor: OIL_RED }}
        />

        {/* Top Brand */}
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-8">
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center shadow-xl"
              style={{ background: `linear-gradient(135deg, ${OIL_RED}, #a3151a)` }}
            >
              <Flame className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="font-bold text-2xl text-white tracking-tight">
                Setu <span style={{ color: OIL_RED }}>AI</span>
              </div>
              <div className="text-xs font-medium" style={{ color: 'rgba(255,255,255,0.5)' }}>
                SIH26122 · Oil India Progress Verification
              </div>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-white leading-snug mt-12">
            Smart Infrastructure<br />
            <span style={{ color: OIL_RED }}>Progress Tracking</span><br />
            for Oil India
          </h2>

          <p className="text-sm mt-4" style={{ color: 'rgba(255,255,255,0.6)', lineHeight: '1.7' }}>
            AI-assisted field progress claims, Primavera P6 schedule compliance,
            and real-time supervisor approval workflow for Oil India infrastructure projects.
          </p>
        </div>

        {/* Feature Highlights */}
        <div className="relative z-10 space-y-3">
          {[
            { icon: ShieldCheck, label: 'Human-in-the-Loop Supervisor Sign-off' },
            { icon: Droplets, label: 'Primavera P6 Baseline Integration' },
            { icon: Flame, label: 'Voice & OCR Claim Ingestion' },
          ].map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-3">
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style={{ backgroundColor: 'rgba(227,30,36,0.15)', border: `1px solid rgba(227,30,36,0.3)` }}
              >
                <Icon className="w-4 h-4" style={{ color: OIL_RED }} />
              </div>
              <span className="text-sm" style={{ color: 'rgba(255,255,255,0.75)' }}>{label}</span>
            </div>
          ))}
          <p className="text-xs pt-4" style={{ color: 'rgba(255,255,255,0.3)' }}>
            Smart India Hackathon 2026 · Problem Statement SIH26122
          </p>
        </div>
      </div>

      {/* ── RIGHT PANEL — Login Form ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 lg:p-12 relative">

        {/* Theme Toggle — top right */}
        <div className="absolute top-4 right-4">
          <Button
            variant="outline"
            size="sm"
            onClick={toggleTheme}
            className="h-9 px-3 gap-2 text-xs rounded-xl shadow-sm"
            style={{
              borderColor: theme === 'dark' ? 'rgba(255,255,255,0.15)' : '#CBD5E1',
              backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.05)' : '#FFFFFF',
              color: theme === 'dark' ? 'rgba(255,255,255,0.85)' : '#334155',
            }}
          >
            {theme === 'dark'
              ? <><Sun className="w-4 h-4 text-amber-400" />Light Mode</>
              : <><Moon className="w-4 h-4" style={{ color: OIL_GRAY }} />Dark Mode</>
            }
          </Button>
        </div>

        {/* Mobile brand badge */}
        <div className="flex lg:hidden items-center gap-2 mb-8">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center"
            style={{ background: `linear-gradient(135deg, ${OIL_RED}, #a3151a)` }}
          >
            <Flame className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="font-bold text-xl tracking-tight" style={{ color: OIL_BLACK }}>
              Setu <span style={{ color: OIL_RED }}>AI</span>
            </div>
            <div className="text-[10px] text-slate-500 font-medium">SIH26122 · Oil India</div>
          </div>
        </div>

        {/* Login Card */}
        <div
          className="w-full max-w-md rounded-2xl shadow-2xl overflow-hidden"
          style={{
            backgroundColor: theme === 'dark' ? 'rgba(43,42,41,0.75)' : '#ffffff',
            border: theme === 'dark' ? '1px solid rgba(255,255,255,0.1)' : '1px solid #CBD5E1',
          }}
        >
          {/* Card header stripe */}
          <div
            className="px-8 py-5 flex items-center justify-between"
            style={{ backgroundColor: OIL_BLACK }}
          >
            <div>
              <h1 className="text-lg font-bold text-white">Sign in to your account</h1>
              <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.55)' }}>
                Authorized Site & Planning Personnel Only
              </p>
            </div>
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center"
              style={{ background: `linear-gradient(135deg, ${OIL_RED}, #a3151a)` }}
            >
              <Flame className="w-5 h-5 text-white" />
            </div>
          </div>

          {/* Orange accent stripe */}
          <div className="h-1" style={{ background: `linear-gradient(90deg, ${OIL_RED}, ${OIL_GRAY})` }} />

          {/* Form body */}
          <div className="px-8 py-7 space-y-5">
            {/* Error banner */}
            {(error || fieldError) && (
              <div className="p-3.5 rounded-xl flex items-start gap-2.5 text-xs"
                style={{ backgroundColor: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#dc2626' }}>
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{fieldError || error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold" style={{ color: theme === 'dark' ? 'rgba(255,255,255,0.8)' : '#374151' }}>
                  Email Address
                </Label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                  <Input
                    type="email"
                    placeholder="name@oilindia.in"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-9 text-sm h-11 rounded-xl"
                    style={{
                      backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.06)' : '#F8FAFC',
                      borderColor: theme === 'dark' ? 'rgba(255,255,255,0.12)' : '#CBD5E1',
                    }}
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold" style={{ color: theme === 'dark' ? 'rgba(255,255,255,0.8)' : '#374151' }}>
                  Password
                </Label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
                  <Input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9 pr-10 text-sm h-11 rounded-xl"
                    style={{
                      backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.06)' : '#F8FAFC',
                      borderColor: theme === 'dark' ? 'rgba(255,255,255,0.12)' : '#CBD5E1',
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-3 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <Button
                type="submit"
                disabled={isLoading}
                className="w-full text-white font-semibold h-11 shadow-lg transition-all flex items-center justify-center gap-2 rounded-xl text-sm"
                style={{
                  background: isLoading ? '#aaa' : `linear-gradient(135deg, ${OIL_RED}, #a3151a)`,
                  boxShadow: `0 4px 18px rgba(227,30,36,0.35)`,
                }}
              >
                {isLoading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </Button>
            </form>

            {/* Demo Credentials */}
            <div className="pt-2 space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px" style={{ backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : '#E2E8F0' }} />
                <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: theme === 'dark' ? 'rgba(255,255,255,0.35)' : '#94A3B8' }}>
                  Demo Access
                </span>
                <div className="flex-1 h-px" style={{ backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.1)' : '#E2E8F0' }} />
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => fillDemo('supervisor@sih26122.internal')}
                  className="p-3 rounded-xl text-left transition-all group"
                  style={{
                    backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.04)' : '#F8FAFC',
                    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.08)' : '#E2E8F0'}`,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = OIL_RED)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(255,255,255,0.08)' : '#E2E8F0')}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold" style={{ color: theme === 'dark' ? '#e2e8f0' : '#1e293b' }}>
                    <ShieldCheck className="w-4 h-4 text-emerald-500" />
                    Supervisor
                  </div>
                  <div className="text-[10px] font-mono mt-0.5 truncate text-slate-400">supervisor@sih26122.internal</div>
                </button>

                <button
                  type="button"
                  onClick={() => fillDemo('site.engineer@sih26122.internal')}
                  className="p-3 rounded-xl text-left transition-all group"
                  style={{
                    backgroundColor: theme === 'dark' ? 'rgba(255,255,255,0.04)' : '#F8FAFC',
                    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.08)' : '#E2E8F0'}`,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = OIL_RED)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = theme === 'dark' ? 'rgba(255,255,255,0.08)' : '#E2E8F0')}
                >
                  <div className="flex items-center gap-1.5 text-xs font-bold" style={{ color: theme === 'dark' ? '#e2e8f0' : '#1e293b' }}>
                    <HardHat className="w-4 h-4 text-amber-500" />
                    Site Engineer
                  </div>
                  <div className="text-[10px] font-mono mt-0.5 truncate text-slate-400">site.engineer@sih26122.internal</div>
                </button>
              </div>
            </div>
          </div>
        </div>

        <p className="text-center text-xs mt-6" style={{ color: theme === 'dark' ? 'rgba(255,255,255,0.3)' : '#94A3B8' }}>
          Smart India Hackathon 2026 · Problem Statement SIH26122
        </p>
      </div>
    </div>
  );
}
