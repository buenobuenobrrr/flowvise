import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useCurrency } from '../contexts/CurrencyContext';
import { useLanguage } from '../contexts/LanguageContext';
import { useNotifications } from '../hooks/useNotifications';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Save, Loader2, User, DollarSign, Palette, Shield } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '../lib/utils';
import {
  ProfileCard, CurrencyCard, IncomeCard, SafetyBufferCard,
  RiskToleranceCard, SubscriptionsCard, NotificationsCard,
  GdprCard, ThemeCard
} from '../components/SettingsCards';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const SECTIONS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'finance', label: 'Finance', icon: DollarSign },
  { id: 'preferences', label: 'Preferences', icon: Palette },
  { id: 'account', label: 'Account', icon: Shield },
];

export default function SettingsPage() {
  const { user, getAuthHeaders, logout } = useAuth();
  const { t } = useLanguage();
  const { fc, currency, setCurrency, currencies } = useCurrency();
  const { supported: notifSupported, isEnabled: notifEnabled, requestPermission } = useNotifications();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeSection, setActiveSection] = useState('profile');
  const [profile, setProfile] = useState({
    income: 0, fixed_costs: 0, safety_buffer: 500,
    risk_tolerance: 'moderate', subscriptions: {}, primary_income: 0
  });

  const fetchProfile = useCallback(async () => {
    try {
      const res = await fetch(`${API}/financial-profile`, { credentials: 'include', headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setProfile({
          income: data.income || 0, fixed_costs: data.fixed_costs || 0,
          safety_buffer: data.safety_buffer || 500,
          risk_tolerance: data.risk_tolerance || 'moderate',
          subscriptions: data.subscriptions || {},
          primary_income: data.primary_income || 0
        });
      }
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Profile load error:', err);
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  }, [getAuthHeaders]);

  useEffect(() => { fetchProfile(); }, [fetchProfile]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { _newSub, ...profileData } = profile;
      const res = await fetch(`${API}/financial-profile`, {
        method: 'PUT', credentials: 'include', headers: getAuthHeaders(),
        body: JSON.stringify(profileData)
      });
      if (!res.ok) throw new Error();
      toast.success('Settings saved');
    } catch (err) {
      if (process.env.NODE_ENV !== 'production') console.error('Profile save error:', err);
      toast.error('Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-background"><Sidebar /><main className="px-5 sm:px-8 lg:px-12 pt-8 lg:pt-10 pb-16"><div className="max-w-4xl mx-auto animate-pulse space-y-6"><div className="h-8 w-48 bg-muted rounded" /><div className="h-64 bg-muted rounded-xl" /></div></main></div>
  );

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="px-5 sm:px-8 lg:px-12 pt-8 lg:pt-10 pb-16" data-testid="settings-page">
        <div className="max-w-4xl mx-auto space-y-10">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="page-title">{t('settings_title')}</h1>
              <p className="text-muted-foreground mt-1 text-sm">{t('settings_subtitle')}</p>
            </div>
            <Button onClick={handleSave} disabled={saving} size="sm" data-testid="save-settings-button">
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
              Save
            </Button>
          </div>

          {/* Section Tabs */}
          <div className="flex gap-1 p-1 bg-muted/50 rounded-xl" data-testid="settings-tabs">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setActiveSection(id)}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all flex-1 justify-center",
                  activeSection === id
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
                data-testid={`settings-tab-${id}`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>

          {/* Section Content */}
          <div className="space-y-6 animate-fade-in" key={activeSection}>
            {activeSection === 'profile' && (
              <>
                <ProfileCard user={user} t={t} />
                <CurrencyCard currency={currency} setCurrency={setCurrency} currencies={currencies} t={t} />
              </>
            )}

            {activeSection === 'finance' && (
              <>
                <IncomeCard profile={profile} setProfile={setProfile} fc={fc} t={t} getAuthHeaders={getAuthHeaders} />
                <SafetyBufferCard profile={profile} setProfile={setProfile} fc={fc} t={t} />
                <RiskToleranceCard profile={profile} setProfile={setProfile} t={t} />
                <SubscriptionsCard profile={profile} setProfile={setProfile} fc={fc} t={t} />
              </>
            )}

            {activeSection === 'preferences' && (
              <>
                <ThemeCard />
                <NotificationsCard notifSupported={notifSupported} notifEnabled={notifEnabled} requestPermission={requestPermission} t={t} />
              </>
            )}

            {activeSection === 'account' && (
              <GdprCard getAuthHeaders={getAuthHeaders} onAccountDeleted={logout} />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
