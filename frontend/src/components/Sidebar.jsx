import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { LanguagePicker } from './LanguagePicker';
import { useState } from 'react';
import {
  LayoutDashboard, Building2, CreditCard, Bell, TrendingUp, LineChart,
  Sparkles, Settings, LogOut, Menu, X, ChevronLeft, PieChart
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'nav_overview' },
  { to: '/dashboard/spending', icon: CreditCard, label: 'nav_spending' },
  { to: '/dashboard/budgets', icon: Bell, label: 'nav_budget_alerts' },
  { to: '/dashboard/investments', icon: TrendingUp, label: 'nav_investments' },
  { to: '/dashboard/portfolio', icon: PieChart, label: 'nav_portfolio' },
  { to: '/dashboard/advisor', icon: Sparkles, label: 'nav_ai_advisor' },
  { to: '/dashboard/simulator', icon: LineChart, label: 'nav_simulator' },
  { to: '/dashboard/accounts', icon: Building2, label: 'nav_bank_accounts' },
  { to: '/dashboard/settings', icon: Settings, label: 'nav_settings' },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const { t } = useLanguage();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/auth');
  };

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-border/50">
        <img src="https://customer-assets.emergentagent.com/job_money-brain-ai/artifacts/qw0mtrax_image_2026-04-27_214300149.png" alt="FlowVise" className="w-7 h-7 rounded" />
        {!collapsed && <span className="font-heading text-lg font-semibold tracking-tight">FlowVise</span>}
        <div className="ml-auto"><LanguagePicker /></div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto" data-testid="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/dashboard'}
            onClick={() => setMobileOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
              }`
            }
            data-testid={`nav-${label}`}
          >
            <Icon className="w-[18px] h-[18px]" strokeWidth={1.5} />
            {!collapsed && <span>{t(label)}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User Section */}
      <div className="px-3 py-4 border-t border-border/50">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-medium text-primary">
            {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || '?'}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name || 'User'}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          )}
        </div>
        <button onClick={handleLogout}
          className="flex items-center gap-3 w-full px-3 py-2 mt-1 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
          data-testid="logout-button">
          <LogOut className="w-[18px] h-[18px]" strokeWidth={1.5} />
          {!collapsed && <span>{t('sign_out')}</span>}
        </button>
      </div>

      {/* Collapse toggle (desktop only) */}
      <button onClick={() => setCollapsed(!collapsed)}
        className="hidden lg:flex items-center justify-center py-3 border-t border-border/50 text-muted-foreground hover:text-foreground transition-colors"
        data-testid="collapse-sidebar">
        <ChevronLeft className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
      </button>
    </div>
  );

  return (
    <>
      {/* Mobile trigger */}
      <button onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-card border border-border shadow-sm"
        data-testid="mobile-menu-trigger">
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-card border-r border-border shadow-xl animate-slide-up">
            <button onClick={() => setMobileOpen(false)} className="absolute top-4 right-4 p-1 text-muted-foreground">
              <X className="w-5 h-5" />
            </button>
            <SidebarContent />
          </aside>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className={`hidden lg:block fixed left-0 top-0 bottom-0 bg-card border-r border-border z-40 transition-all duration-200 ${collapsed ? 'w-16' : 'w-60'}`}
        data-testid="sidebar">
        <SidebarContent />
      </aside>
    </>
  );
}
