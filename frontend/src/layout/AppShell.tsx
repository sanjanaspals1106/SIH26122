import React, { useState, useEffect } from 'react';
import { Outlet, Navigate, useLocation, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { useTheme } from '@/theme/ThemeProvider';
import {
  LayoutDashboard,
  ClipboardList,
  Layers,
  Clock,
  Activity,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  PlusCircle,
  HardHat,
  ShieldCheck,
  Building2,
  Sun,
  Moon,
  Flame,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const SIDEBAR_COLLAPSED_KEY = 'setu_sidebar_collapsed_v1';

// Oil India Limited (OIL) brand tokens
const OIL = {
  black:   '#2B2A29',   // OIL black – sidebar/header bg
  red:     '#E31E24',   // OIL red – CTA, active nav, brand accents
  blackDark: '#201F1E', // sidebar footer, slightly darker than black
  blackLight: '#3D3B39', // slightly lighter black for hover states
};

export default function AppShell() {
  const { user, isAuthenticated, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true';
  });
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(isCollapsed));
  }, [isCollapsed]);

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const isSupervisor = user.role === 'SUPERVISOR';

  const supervisorNavItems = [
    { label: 'Daily Digest',      path: '/digest',    icon: ClipboardList },
    { label: 'Review Workspace',  path: '/review',    icon: Layers },
    { label: 'Dashboard',         path: '/dashboard', icon: LayoutDashboard },
    { label: 'Activity History',  path: '/history',   icon: Clock },
    { label: 'Impact Preview',    path: '/impact',    icon: Activity },
  ];

  const siteEngineerNavItems = [
    { label: 'Claim Intake', path: '/intake', icon: PlusCircle },
  ];

  const navItems = isSupervisor ? supervisorNavItems : siteEngineerNavItems;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div
      className="min-h-screen flex font-sans antialiased selection:bg-[#E31E24] selection:text-white transition-colors duration-200"
      style={{ backgroundColor: theme === 'dark' ? '#1a1918' : '#FFFFFF' }}
    >
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* ── LEFT SIDEBAR ─────────────────────────────────────────────────────── */}
      <aside
        style={{ backgroundColor: OIL.black }}
        className={cn(
          'fixed lg:static top-0 bottom-0 left-0 z-50 flex flex-col justify-between transition-all duration-300 ease-in-out shadow-2xl',
          isCollapsed ? 'lg:w-[72px]' : 'lg:w-64',
          isMobileOpen ? 'w-64 translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Sidebar Header — Brand */}
        <div
          className="p-4 flex items-center justify-between border-b"
          style={{ borderColor: 'rgba(255,255,255,0.12)' }}
        >
          <div className="flex items-center gap-3 overflow-hidden">
            {/* OIL-inspired flame icon in red circle */}
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 shadow-lg"
              style={{ background: `linear-gradient(135deg, ${OIL.red}, #a3151a)` }}
            >
              <Flame className="w-5 h-5 text-white" />
            </div>
            {!isCollapsed && (
              <div className="flex flex-col min-w-0">
                <span className="font-bold text-base text-white leading-tight truncate tracking-tight">
                  Setu <span style={{ color: OIL.red }}>AI</span>
                </span>
                <span className="text-[10px] font-semibold tracking-wider truncate" style={{ color: 'rgba(255,255,255,0.55)' }}>
                  SIH26122 · Oil India
                </span>
              </div>
            )}
          </div>

          {/* Desktop Collapse Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="hidden lg:flex h-8 w-8 rounded-lg text-white/60 hover:text-white hover:bg-white/10"
            title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </Button>

          {/* Mobile Close Button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsMobileOpen(false)}
            className="lg:hidden text-white/60 hover:text-white h-8 w-8"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive =
              location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsMobileOpen(false)}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium text-sm transition-all group',
                  isActive
                    ? 'text-white shadow-md'
                    : 'text-white/65 hover:text-white hover:bg-white/10'
                )}
                style={isActive ? { backgroundColor: OIL.red, boxShadow: `0 4px 16px rgba(227,30,36,0.35)` } : {}}
                title={isCollapsed ? item.label : undefined}
              >
                <Icon
                  className={cn(
                    'w-5 h-5 shrink-0 transition-transform group-hover:scale-110',
                    isActive ? 'text-white' : 'text-white/50 group-hover:text-white'
                  )}
                />
                {!isCollapsed && (
                  <span className="whitespace-nowrap">{item.label}</span>
                )}
                {/* Collapsed tooltip pip */}
                {isCollapsed && isActive && (
                  <span
                    className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-l-full"
                    style={{ backgroundColor: OIL.red }}
                  />
                )}
              </Link>
            );
          })}
        </div>

        {/* Sidebar Footer — User & Logout */}
        <div
          className="p-3 border-t space-y-2"
          style={{ borderColor: 'rgba(255,255,255,0.12)', backgroundColor: OIL.blackDark }}
        >
          {!isCollapsed && (
            <div className="flex items-center gap-3 px-1 py-1">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 border"
                style={{ backgroundColor: 'rgba(255,255,255,0.08)', borderColor: 'rgba(255,255,255,0.15)' }}
              >
                {isSupervisor
                  ? <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  : <HardHat className="w-5 h-5 text-amber-400" />}
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-sm font-semibold text-white truncate">{user.full_name}</span>
                <span className="text-xs font-medium truncate flex items-center gap-1.5" style={{ color: 'rgba(255,255,255,0.55)' }}>
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ backgroundColor: isSupervisor ? '#10b981' : '#f59e0b' }}
                  />
                  {isSupervisor ? 'Supervisor' : 'Site Engineer'}
                </span>
              </div>
            </div>
          )}

          <Button
            variant="ghost"
            onClick={handleLogout}
            className={cn(
              'w-full font-semibold rounded-lg transition-colors',
              isCollapsed ? 'h-9 w-9 p-0' : 'h-10 justify-start gap-2 px-3'
            )}
            style={{ color: 'rgba(255,255,255,0.75)', backgroundColor: 'rgba(255,255,255,0.06)' }}
            onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(227,30,36,0.15)'; e.currentTarget.style.color = '#ff8a8f'; }}
            onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = 'rgba(255,255,255,0.75)'; }}
            title="Sign Out"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            {!isCollapsed && <span className="text-sm">Sign Out</span>}
          </Button>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen overflow-x-hidden">
        {/* Top Header Bar */}
        <header
          className="h-16 px-4 lg:px-8 flex items-center justify-between sticky top-0 z-30 shadow-md transition-colors duration-200"
          style={{
            backgroundColor: theme === 'dark' ? OIL.black : OIL.black,
            borderBottom: `3px solid ${OIL.red}`,
          }}
        >
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsMobileOpen(true)}
              className="lg:hidden text-white/80 hover:text-white hover:bg-white/10"
            >
              <Menu className="w-5 h-5" />
            </Button>

            {/* Live status badge */}
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs font-mono font-medium hidden sm:inline" style={{ color: 'rgba(255,255,255,0.65)' }}>
                Primavera P6 v3.2 · Live
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              className="text-white/70 hover:text-white hover:bg-white/10 h-8 px-3 gap-1.5 text-xs rounded-xl border border-white/15"
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
            >
              {theme === 'dark'
                ? <><Sun className="w-3.5 h-3.5 text-amber-300" /><span className="hidden sm:inline">Light</span></>
                : <><Moon className="w-3.5 h-3.5 text-blue-300" /><span className="hidden sm:inline">Dark</span></>
              }
            </Button>

            {/* Human-in-the-Loop Badge */}
            <div
              className="px-3 py-1 rounded-full text-[11px] font-mono font-semibold flex items-center gap-1.5 border"
              style={{
                backgroundColor: 'rgba(227,30,36,0.15)',
                borderColor: 'rgba(227,30,36,0.35)',
                color: '#E31E24',
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: '#E31E24' }} />
              <span className="hidden sm:inline">Human-in-the-Loop</span>
              <span className="sm:hidden">HIL</span>
            </div>
          </div>
        </header>

        {/* Main Content Viewport */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
