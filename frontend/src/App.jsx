import { useState, useEffect } from 'react';
import './App.css';
import { getCurrentUser, getCsrfToken, logoutUser } from './services/api';
import Login from './components/Login';
import Signup from './components/Signup';
import Dashboard from './components/Dashboard';

function App() {
  const [user, setUser] = useState(null);
  const [currentCompany, setCurrentCompany] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [view, setView] = useState('login'); // 'login' | 'signup' | 'authenticated'
  const [loading, setLoading] = useState(true);

  // Initialize session and fetch current authenticated user
  useEffect(() => {
    async function initAuth() {
      try {
        await getCsrfToken();
        const authData = await getCurrentUser();
        if (authData && authData.isAuthenticated) {
          setUser(authData.user);
          setCurrentCompany(authData.current_company);
          setCompanies(authData.companies || []);
          setView('authenticated');
        }
      } catch (err) {
        console.error('Failed to initialize auth:', err);
      } finally {
        setLoading(false);
      }
    }

    initAuth();
  }, []);

  const handleLoginSuccess = (data) => {
    setUser(data.user);
    setCurrentCompany(data.current_company || null);
    setCompanies(data.companies || []);
    setView('authenticated');
  };

  const handleSignupSuccess = (data) => {
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
      await logoutUser();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
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
