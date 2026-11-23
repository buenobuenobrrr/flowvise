import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { LanguagePicker } from './LanguagePicker';
import { FlowMark } from './FlowMark';
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

  const linkClass = ({ isActive }) =>
    `flex items-center gap-2 px-3 py-2.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
      isActive
        ? 'border-primary text-foreground font-medium'
        : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
    }`;

  return (
    <>
      <header
        className="sticky top-0 z-40 bg-card border-b border-border"
        data-testid="sidebar"
      >
        <div className="flex items-center gap-3 px-4 sm:px-8 h-14">
          <FlowMark className="w-7 h-7" />
          <span className="font-heading text-xl leading-none text-foreground">FlowVise</span>
          <div className="ml-auto flex items-center gap-2">
            <LanguagePicker compact />
            <div className="hidden md:block text-right min-w-0 max-w-[180px]">
              <p className="text-sm font-medium truncate">{user?.name || 'User'}</p>
              <p className="text-[11px] text-muted-foreground truncate">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1.5 text-sm text-muted-foreground hover:text-foreground"
              data-testid="logout-button"
            >
              <LogOut className="w-4 h-4" strokeWidth={1.5} />
              <span>{t('sign_out')}</span>
            </button>
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="hidden lg:inline-flex items-center justify-center p-1.5 text-muted-foreground hover:text-foreground"
              data-testid="collapse-sidebar"
              aria-label="Toggle navigation"
            >
              <ChevronLeft className={`w-4 h-4 transition-transform ${collapsed ? '-rotate-90' : 'rotate-90'}`} />
            </button>
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 rounded-md border border-border"
              data-testid="mobile-menu-trigger"
            >
              <Menu className="w-5 h-5" />
            </button>
          </div>
        </div>
        {!collapsed && (
          <nav className="hidden lg:flex items-center gap-0.5 px-4 sm:px-6 overflow-x-auto" data-testid="sidebar-nav">
            {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
              <NavLink key={to} to={to} end={to === '/dashboard'} className={linkClass} data-testid={`nav-${label}`}>
                <Icon className="w-4 h-4" strokeWidth={1.5} />
                <span>{t(label)}</span>
              </NavLink>
            ))}
          </nav>
        )}
      </header>

      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-[hsl(216_28%_10%/0.4)]" onClick={() => setMobileOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-72 bg-card border-r border-border shadow-card">
            <button onClick={() => setMobileOpen(false)} className="absolute top-4 right-4 p-1 text-muted-foreground">
              <X className="w-5 h-5" />
            </button>
            <div className="px-5 pt-6 pb-3 font-heading text-xl">FlowVise</div>
            <nav className="px-3 py-2 space-y-0.5" data-testid="sidebar-nav-mobile">
              {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
                <NavLink key={to} to={to} end={to === '/dashboard'}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 text-sm border-l-2 ${
                      isActive ? 'border-primary text-foreground font-medium' : 'border-transparent text-muted-foreground'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" strokeWidth={1.5} />
                  <span>{t(label)}</span>
                </NavLink>
              ))}
            </nav>
            <button onClick={handleLogout} className="flex items-center gap-3 w-full px-6 py-3 mt-2 text-sm text-muted-foreground">
              <LogOut className="w-4 h-4" strokeWidth={1.5} />
              <span>{t('sign_out')}</span>
            </button>
          </aside>
        </div>
      )}
    </>
  );
}
