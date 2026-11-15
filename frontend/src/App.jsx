import { useState, useEffect } from 'react';
import './App.css';
import { getCurrentUser, getCsrfToken, logoutUser, setOnAuthFailure } from './services/api';
import Login from './components/Login';
import Signup from './components/Signup';
import Dashboard from './components/Dashboard';

const TAB_SESSION_KEY = 'invoiceflow_tab_session';
const TAB_UNLOAD_KEY = 'invoiceflow_tab_unloaded_at';
const AUTH_BROADCAST_CHANNEL = 'invoiceflow_auth_channel';
const MAX_RELOAD_INTERVAL_MS = 20000; // 20-second threshold to distinguish page refreshes from browser restarts

function isPageReloadOrHistory() {
  try {
    const navEntries = typeof performance !== 'undefined' && performance.getEntriesByType ? performance.getEntriesByType('navigation') : [];
    if (navEntries.length > 0) {
      const type = navEntries[0].type;
      return type === 'reload' || type === 'back_forward';
    }
    if (typeof performance !== 'undefined' && performance.navigation) {
      return performance.navigation.type === 1 || performance.navigation.type === 2;
    }
  } catch {
    // ignore
  }
  return false;
}

function getTabSession() {
  try {
    const raw = sessionStorage.getItem(TAB_SESSION_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw);

    // Validate window.name matches tabId to protect against tab duplication and fresh tab access
    if (!window.name || !session.tabId || window.name !== session.tabId) {
      sessionStorage.removeItem(TAB_SESSION_KEY);
      sessionStorage.removeItem(TAB_UNLOAD_KEY);
      return null;
    }

    // Check for Chrome session restore after browser restart
    const unloadedAt = sessionStorage.getItem(TAB_UNLOAD_KEY);
    if (unloadedAt) {
      sessionStorage.removeItem(TAB_UNLOAD_KEY);
      const elapsed = Date.now() - Number(unloadedAt);
      // Legitimate user page refreshes and history traversals must not be invalidated by load delay
      if (!isPageReloadOrHistory() && elapsed > MAX_RELOAD_INTERVAL_MS) {
        // Tab was restored after browser shutdown / long suspension
        sessionStorage.removeItem(TAB_SESSION_KEY);
        window.name = '';
        return null;
      }
    }

    return session;
  } catch {
    sessionStorage.removeItem(TAB_SESSION_KEY);
    sessionStorage.removeItem(TAB_UNLOAD_KEY);
    return null;
  }
}

function setTabSession(userId, username) {
  const tabId = `tab_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
  window.name = tabId;
  const session = {
    tabId,
    userId,
    username,
    authenticatedAt: Date.now(),
  };
  sessionStorage.setItem(TAB_SESSION_KEY, JSON.stringify(session));
  sessionStorage.removeItem(TAB_UNLOAD_KEY);
  return session;
}

function clearTabSession() {
  try {
    sessionStorage.removeItem(TAB_SESSION_KEY);
    sessionStorage.removeItem(TAB_UNLOAD_KEY);
    window.name = '';
  } catch {
    // ignore
  }
}

function App() {
  const [user, setUser] = useState(null);
  const [currentCompany, setCurrentCompany] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [view, setView] = useState('login'); // 'login' | 'signup' | 'authenticated'
  const [loading, setLoading] = useState(true);

  // Record unload timestamp so refreshes can be recognized while browser restarts are expired
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (sessionStorage.getItem(TAB_SESSION_KEY)) {
        sessionStorage.setItem(TAB_UNLOAD_KEY, String(Date.now()));
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Listen for cross-tab logout events to avoid displaying stale authenticated UI
  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return;
    try {
      const channel = new BroadcastChannel(AUTH_BROADCAST_CHANNEL);
      channel.onmessage = (event) => {
        if (event?.data?.type === 'LOGOUT') {
          clearTabSession();
          setUser(null);
          setCurrentCompany(null);
          setCompanies([]);
          setView('login');
        }
      };
      return () => {
        channel.close();
      };
    } catch {
      // ignore
    }
  }, []);

  // Initialize session and fetch current authenticated user for this specific tab
  useEffect(() => {
    setOnAuthFailure(() => {
      clearTabSession();
      setUser(null);
      setCurrentCompany(null);
      setCompanies([]);
      setView('login');
    });

    async function initAuth() {
      try {
        await getCsrfToken();
        const tabSession = getTabSession();

        if (tabSession) {
          const authData = await getCurrentUser();
          if (
            authData &&
            authData.isAuthenticated &&
            authData.user &&
            authData.user.id === tabSession.userId
          ) {
            setUser(authData.user);
            setCurrentCompany(authData.current_company);
            setCompanies(authData.companies || []);
            setView('authenticated');
          } else {
            // Server session expired, flushed, or user mismatch
            clearTabSession();
            setView('login');
          }
        } else {
          // Brand-new tab, closed tab, or restored tab: require login
          clearTabSession();
          setView('login');
        }
      } catch (err) {
        console.error('Failed to initialize auth:', err);
        clearTabSession();
        setView('login');
      } finally {
        setLoading(false);
      }
    }

    initAuth();
  }, []);

  const handleLoginSuccess = (data) => {
    if (data?.user?.id) {
      setTabSession(data.user.id, data.user.username);
    }
    setUser(data.user);
    setCurrentCompany(data.current_company || null);
    setCompanies(data.companies || []);
    setView('authenticated');
  };

  const handleSignupSuccess = (data) => {
    if (data?.user?.id) {
      setTabSession(data.user.id, data.user.username);
    }
    setUser(data.user);
    setCurrentCompany(data.current_company || null);
    setCompanies(data.companies || []);
    setView('authenticated');
  };

  const handleCompanyUpdated = (updatedCompany, updatedCompanies) => {
    setCurrentCompany(updatedCompany);
    setCompanies(updatedCompanies);
  };

  const handleLogout = async () => {
    try {
      if (typeof BroadcastChannel !== 'undefined') {
        const channel = new BroadcastChannel(AUTH_BROADCAST_CHANNEL);
        channel.postMessage({ type: 'LOGOUT' });
        channel.close();
      }
    } catch {
      // ignore
    }
    try {
      await logoutUser();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      clearTabSession();
      setUser(null);
      setCurrentCompany(null);
      setCompanies([]);
      setView('login');
      getCsrfToken().catch(() => {});
    }
  };

  if (loading) {
    return (
      <div className="app-shell">
        <div className="loading-spinner">Loading InvoiceFlow...</div>
      </div>
    );
  }

  // Authenticated view renders the full Dashboard
  if (view === 'authenticated' && user) {
    return (
      <div className="app-shell">
        <Dashboard
          user={user}
          currentCompany={currentCompany}
          companies={companies}
          onCompanyUpdated={handleCompanyUpdated}
          onLogout={handleLogout}
        />
      </div>
    );
  }

  // Unauthenticated view renders Login or Signup
  return (
    <div className="app-shell">
      <div className="auth-container">
        <header className="auth-header">
          <span className="brand-badge">InvoiceFlow</span>
          <h1 className="auth-title">
            {view === 'signup' ? 'Create an account' : 'Welcome back'}
          </h1>
          <p className="auth-subtitle">
            {view === 'signup'
              ? 'Get started with your invoicing workspace'
              : 'Enter your credentials to access your workspace'}
          </p>
        </header>

        {view === 'signup' ? (
          <Signup
            onSignupSuccess={handleSignupSuccess}
            onSwitchToLogin={() => setView('login')}
          />
        ) : (
          <Login
            onLoginSuccess={handleLoginSuccess}
            onSwitchToSignup={() => setView('signup')}
          />
        )}
      </div>
    </div>
  );
}

export default App;
