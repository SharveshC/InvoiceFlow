import { useState } from 'react';
import { createCompany, switchCompany } from '../services/api';
import Customers from './Customers';
import Products from './Products';
import Invoices from './Invoices';
import Payments from './Payments';
import Reports from './Reports';

function Dashboard({ user, currentCompany, companies = [], onCompanyUpdated, onLogout }) {
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'clients' | 'products' | 'invoices' | 'payments' | 'reports'
  const [showCreateForm, setShowCreateForm] = useState(companies.length === 0);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [gstNumber, setGstNumber] = useState('');
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [switchingId, setSwitchingId] = useState(null);

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    if (!name.trim() || !email.trim() || !phone.trim() || !address.trim()) {
      setFormError('Please fill in all required fields.');
      return;
    }

    setLoading(true);
    try {
      const response = await createCompany({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        address: address.trim(),
        gst_number: gstNumber.trim() || null,
      });

      setName('');
      setEmail('');
      setPhone('');
      setAddress('');
      setGstNumber('');
      setFormSuccess('Company created successfully.');
      setShowCreateForm(false);

      if (onCompanyUpdated) {
        onCompanyUpdated(response.current_company, response.companies);
      }
    } catch (err) {
      setFormError(err.message || 'Failed to create company.');
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchCompany = async (companyId) => {
    if (currentCompany && currentCompany.id === companyId) return;

    setFormError('');
    setFormSuccess('');
    setSwitchingId(companyId);

    try {
      const response = await switchCompany(companyId);
      setFormSuccess(`Switched to ${response.current_company?.name || 'company'} successfully.`);

      if (onCompanyUpdated) {
        onCompanyUpdated(response.current_company, response.companies);
      }
    } catch (err) {
      setFormError(err.message || 'Failed to switch company.');
    } finally {
      setSwitchingId(null);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Top Header Bar */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1 className="header-brand-title">InvoiceFlow</h1>
          {currentCompany && (
            <div className="header-pill">
              <span>{currentCompany.name}</span>
              {currentCompany.role && (
                <span className="role-badge">{currentCompany.role}</span>
              )}
            </div>
          )}
        </div>

        <div className="header-right">
          <div className="user-profile-badge">
            <span className="user-avatar">
              {(user?.first_name || user?.username || 'U')[0].toUpperCase()}
            </span>
            <div className="user-details">
              <span className="user-name">{user?.first_name || user?.username}</span>
              <span className="user-email">{user?.email}</span>
            </div>
          </div>

          <button
            type="button"
            className="btn-secondary btn-small"
            onClick={onLogout}
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Horizontal Navigation Tabs */}
      <nav className="dashboard-nav">
        <button
          type="button"
          className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          Dashboard
        </button>
        <button
          type="button"
          className={`nav-item ${activeTab === 'clients' ? 'active' : ''}`}
          onClick={() => setActiveTab('clients')}
        >
          Clients
        </button>
        <button
          type="button"
          className={`nav-item ${activeTab === 'products' ? 'active' : ''}`}
          onClick={() => setActiveTab('products')}
        >
          Products
        </button>
        <button
          type="button"
          className={`nav-item ${activeTab === 'invoices' ? 'active' : ''}`}
          onClick={() => setActiveTab('invoices')}
        >
          Invoices
        </button>
        <button
          type="button"
          className={`nav-item ${activeTab === 'payments' ? 'active' : ''}`}
          onClick={() => setActiveTab('payments')}
        >
          Payments
        </button>
        <button
          type="button"
          className={`nav-item ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          Reports & Analytics
        </button>
      </nav>

      {/* Status Alerts */}
      {formSuccess && (
        <div className="dashboard-alert success">
          <span>{formSuccess}</span>
          <button
            type="button"
            className="alert-close"
            onClick={() => setFormSuccess('')}
          >
            ✕
          </button>
        </div>
      )}

      {formError && (
        <div className="dashboard-alert error">
          <span>{formError}</span>
          <button
            type="button"
            className="alert-close"
            onClick={() => setFormError('')}
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Content */}
      <main>
        {companies.length === 0 ? (
          <section className="card">
            <div className="card-header-flex">
              <div>
                <span className="brand-badge">Onboarding</span>
                <h2 className="card-title" style={{ fontSize: '18px', marginTop: '6px' }}>
                  Set up your company profile
                </h2>
                <p className="card-subtitle">
                  Create your business profile to begin managing clients and invoices.
                </p>
              </div>
            </div>

            <form onSubmit={handleCreateCompany} className="company-form" style={{ marginTop: '20px' }}>
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="comp-name">Company Name *</label>
                  <input
                    id="comp-name"
                    type="text"
                    placeholder="Acme Corporation"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="comp-email">Company Email *</label>
                  <input
                    id="comp-email"
                    type="email"
                    placeholder="billing@acme.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="comp-phone">Phone Number *</label>
                  <input
                    id="comp-phone"
                    type="text"
                    placeholder="9876543210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="comp-gst">GST Number (Optional)</label>
                  <input
                    id="comp-gst"
                    type="text"
                    placeholder="22AAAAA0000A1Z5"
                    value={gstNumber}
                    onChange={(e) => setGstNumber(e.target.value)}
                    disabled={loading}
                  />
                </div>

                <div className="form-group full-width">
                  <label htmlFor="comp-address">Billing Address *</label>
                  <textarea
                    id="comp-address"
                    rows="3"
                    placeholder="123 Business Avenue, Suite 400..."
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Creating...' : 'Create Company Profile'}
                </button>
              </div>
            </form>
          </section>
        ) : activeTab === 'clients' ? (
          <Customers currentCompany={currentCompany} />
        ) : activeTab === 'products' ? (
          <Products currentCompany={currentCompany} />
        ) : activeTab === 'invoices' ? (
          <Invoices currentCompany={currentCompany} />
        ) : activeTab === 'payments' ? (
          <Payments currentCompany={currentCompany} />
        ) : activeTab === 'reports' ? (
          <Reports currentCompany={currentCompany} />
        ) : (
          <>
            {/* Active Company Overview Card */}
            <section className="card">
              <div className="card-header-flex">
                <div>
                  <span className="detail-label">Active Company</span>
                  <h2 className="company-heading">
                    {currentCompany?.name}
                    {currentCompany?.role && (
                      <span className="role-badge">{currentCompany.role}</span>
                    )}
                  </h2>
                </div>

                <button
                  type="button"
                  className="btn-secondary btn-small"
                  onClick={() => setShowCreateForm(!showCreateForm)}
                >
                  {showCreateForm ? 'Cancel' : '+ Add Company'}
                </button>
              </div>

              <div className="company-details-grid">
                <div className="detail-item">
                  <span className="detail-label">Email</span>
                  <span className="detail-value">{currentCompany?.email || '—'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Phone</span>
                  <span className="detail-value">{currentCompany?.phone || '—'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">GST Number</span>
                  <span className="detail-value">{currentCompany?.gst_number || 'None'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Address</span>
                  <span className="detail-value">{currentCompany?.address || '—'}</span>
                </div>
              </div>
            </section>

            {/* Create Another Company Form (toggled) */}
            {showCreateForm && (
              <section className="card">
                <div className="card-header-flex">
                  <div>
                    <h3 className="card-title">Add New Company</h3>
                    <p className="card-subtitle">Create and switch to another business profile.</p>
                  </div>
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => setShowCreateForm(false)}
                  >
                    Close
                  </button>
                </div>

                <form onSubmit={handleCreateCompany} className="company-form" style={{ marginTop: '16px' }}>
                  <div className="form-grid">
                    <div className="form-group">
                      <label htmlFor="new-comp-name">Company Name *</label>
                      <input
                        id="new-comp-name"
                        type="text"
                        placeholder="Beta Logistics"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        disabled={loading}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="new-comp-email">Company Email *</label>
                      <input
                        id="new-comp-email"
                        type="email"
                        placeholder="billing@betalogistics.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={loading}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="new-comp-phone">Phone Number *</label>
                      <input
                        id="new-comp-phone"
                        type="text"
                        placeholder="9876543210"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        disabled={loading}
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="new-comp-gst">GST Number (Optional)</label>
                      <input
                        id="new-comp-gst"
                        type="text"
                        placeholder="33BBBBB0000B1Z6"
                        value={gstNumber}
                        onChange={(e) => setGstNumber(e.target.value)}
                        disabled={loading}
                      />
                    </div>

                    <div className="form-group full-width">
                      <label htmlFor="new-comp-address">Billing Address *</label>
                      <textarea
                        id="new-comp-address"
                        rows="3"
                        placeholder="456 Industrial Sector..."
                        value={address}
                        onChange={(e) => setAddress(e.target.value)}
                        disabled={loading}
                        required
                      />
                    </div>
                  </div>

                  <div className="form-actions">
                    <button type="submit" className="btn-primary" disabled={loading}>
                      {loading ? 'Creating...' : 'Create & Switch Company'}
                    </button>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => setShowCreateForm(false)}
                      disabled={loading}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </section>
            )}

            {/* Company Switcher List */}
            <section className="card">
              <h3 className="card-title">Your Companies ({companies.length})</h3>
              <p className="card-subtitle">
                Switch your active company to manage invoices and clients for that workspace.
              </p>

              <div className="companies-list">
                {companies.map((c) => {
                  const isActive = currentCompany && currentCompany.id === c.id;
                  const isSwitching = switchingId === c.id;

                  return (
                    <div
                      key={c.id}
                      className={`company-item-card ${isActive ? 'active-item' : ''}`}
                    >
                      <div className="company-item-info">
                        <div className="company-name-row">
                          <span className="item-company-name">{c.name}</span>
                          {c.role && <span className="role-badge">{c.role}</span>}
                          {isActive && <span className="active-tag">Active</span>}
                        </div>
                        <span className="item-company-email">{c.email}</span>
                      </div>

                      <div>
                        {isActive ? (
                          <span className="active-tag">Current Workspace</span>
                        ) : (
                          <button
                            type="button"
                            className="btn-secondary btn-small"
                            onClick={() => handleSwitchCompany(c.id)}
                            disabled={isSwitching}
                          >
                            {isSwitching ? 'Switching...' : 'Switch'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Quick Module Launchers */}
            <section className="modules-grid">
              <div
                className="module-card clickable-module"
                onClick={() => setActiveTab('clients')}
              >
                <div>
                  <h4>Clients & Customers</h4>
                  <p>Manage customer profiles, billing addresses, and GST numbers.</p>
                </div>
                <span className="module-action-link">Open Clients &rarr;</span>
              </div>

              <div
                className="module-card clickable-module"
                onClick={() => setActiveTab('products')}
              >
                <div>
                  <h4>Products & Services</h4>
                  <p>Catalog items, tax rates, standard pricing, and descriptions.</p>
                </div>
                <span className="module-action-link">Open Products &rarr;</span>
              </div>

              <div
                className="module-card clickable-module"
                onClick={() => setActiveTab('invoices')}
              >
                <div>
                  <h4>Invoices</h4>
                  <p>Draft, dispatch, and export professional PDF invoices.</p>
                </div>
                <span className="module-action-link">Open Invoices &rarr;</span>
              </div>

              <div
                className="module-card clickable-module"
                onClick={() => setActiveTab('payments')}
              >
                <div>
                  <h4>Payments</h4>
                  <p>Record transactions, payment methods, and revenue flow.</p>
                </div>
                <span className="module-action-link">Open Payments &rarr;</span>
              </div>

              <div
                className="module-card clickable-module"
                onClick={() => setActiveTab('reports')}
              >
                <div>
                  <h4>Reports & Analytics</h4>
                  <p>Financial summaries, revenue trends, and audit exports.</p>
                </div>
                <span className="module-action-link">Open Analytics &rarr;</span>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}

export default Dashboard;
