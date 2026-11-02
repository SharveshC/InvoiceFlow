import { useState, useEffect } from 'react';
import './App.css';
import { checkApiHealth } from './services/api';

function App() {
  const [apiStatus, setApiStatus] = useState('checking');
  const [apiData, setApiData] = useState(null);

  useEffect(() => {
    checkApiHealth()
      .then((data) => {
        setApiStatus('connected');
        setApiData(data);
      })
      .catch((err) => {
        setApiStatus('waiting_for_approval');
        setApiData({ error: err.message });
      });
  }, []);

  return (
    <div className="container">
      <header className="header">
        <span className="logo-badge">InvoiceFlow React Migration • Phase 1</span>
        <h1 className="title">Frontend + API Setup</h1>
        <p className="subtitle">
          React frontend running alongside existing Django application
        </p>
      </header>

      <main>
        <section className="card">
          <h2 className="card-title">Backend API Connection</h2>
          <div className="status-box">
            <span
              className={`status-dot ${
                apiStatus === 'connected'
                  ? 'active'
                  : apiStatus === 'waiting_for_approval'
                  ? 'error'
                  : ''
              }`}
            />
            <span className="status-text">
              {apiStatus === 'checking' && 'Checking connection to Django REST Framework...'}
              {apiStatus === 'connected' &&
                `Connected to Django REST Framework: ${apiData?.message || 'Ready'}`}
              {apiStatus === 'waiting_for_approval' &&
                'Awaiting Django settings URL hook approval (or Django server offline)'}
            </span>
          </div>

          <div className="grid">
            <div className="grid-item">
              <div className="grid-label">Frontend</div>
              <div className="grid-value">React + Vite</div>
            </div>
            <div className="grid-item">
              <div className="grid-label">Styling</div>
              <div className="grid-value">Ordinary CSS</div>
            </div>
            <div className="grid-item">
              <div className="grid-label">Backend API</div>
              <div className="grid-value">Django REST Framework</div>
            </div>
            <div className="grid-item">
              <div className="grid-label">Existing HTML App</div>
              <div className="grid-value">100% Intact</div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
