import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { LanguageProvider } from "./contexts/LanguageContext";
import { CurrencyProvider } from "./contexts/CurrencyContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { Toaster } from "./components/ui/sonner";
import { Loader2 } from "lucide-react";

// Pages
import AuthPage from "./pages/AuthPage";
import AuthCallback from "./pages/AuthCallback";
import Dashboard from "./pages/Dashboard";
import BankAccountsPage from "./pages/BankAccountsPage";
import SpendingPage from "./pages/SpendingPage";
import InvestmentsPage from "./pages/InvestmentsPage";
import AIAdvisorPage from "./pages/AIAdvisorPage";
import SettingsPage from "./pages/SettingsPage";
import BudgetAlertsPage from "./pages/BudgetAlertsPage";
import PortfolioSimulatorPage from "./pages/PortfolioSimulatorPage";
import PortfolioPage from "./pages/PortfolioPage";

// Protected Route Component
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Skip auth check if user data was passed from AuthCallback
  if (location.state?.user) {
    return children;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  return children;
}

// Public Route (redirect to dashboard if authenticated)
function PublicRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

// App Router Component
function AppRouter() {
  const location = useLocation();

  // Check URL fragment for session_id (OAuth callback)
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/auth"
        element={
          <PublicRoute>
            <AuthPage />
          </PublicRoute>
        }
      />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/accounts"
        element={
          <ProtectedRoute>
            <BankAccountsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/spending"
        element={
          <ProtectedRoute>
            <SpendingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/investments"
        element={
          <ProtectedRoute>
            <InvestmentsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/advisor"
        element={
          <ProtectedRoute>
            <AIAdvisorPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/budgets"
        element={
          <ProtectedRoute>
            <BudgetAlertsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/simulator"
        element={
          <ProtectedRoute>
            <PortfolioSimulatorPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/portfolio"
        element={
          <ProtectedRoute>
            <PortfolioPage />
          </ProtectedRoute>
        }
      />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/auth" replace />} />
      <Route path="*" element={<Navigate to="/auth" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <ThemeProvider>
          <LanguageProvider>
            <CurrencyProvider>
              <AuthProvider>
                <AppRouter />
                <Toaster position="top-right" richColors />
              </AuthProvider>
            </CurrencyProvider>
          </LanguageProvider>
        </ThemeProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
