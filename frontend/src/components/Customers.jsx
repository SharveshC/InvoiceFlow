import { useState, useEffect, useCallback } from 'react';
import {
  getCustomers,
  createCustomer,
  updateCustomer,
  deleteCustomer,
} from '../services/api';
import CompanyRequiredState from './CompanyRequiredState';

function Customers({ currentCompany, onNavigateToCreateCompany }) {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form State
  const [showForm, setShowForm] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [gstNumber, setGstNumber] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  // Fetch customers helper
  const fetchCustomers = useCallback(async (searchQuery = '') => {
    if (!currentCompany) return;
    setLoading(true);
    try {
      const data = await getCustomers(searchQuery);
      setCustomers(data);
    } catch (err) {
      setError(err.message || 'Failed to load customers.');
    } finally {
      setLoading(false);
    }
  }, [currentCompany]);

  // Load customers whenever currentCompany or search changes (debounced by 300ms)
  useEffect(() => {
    let ignore = false;
    if (!currentCompany) return;

    const delay = search ? 300 : 0;
    const timer = setTimeout(() => {
      getCustomers(search)
        .then((data) => {
          if (!ignore) {
            setCustomers(data);
          }
        })
        .catch((err) => {
          if (!ignore) {
            setError(err.message || 'Failed to load customers.');
          }
        })
        .finally(() => {
          if (!ignore) {
            setLoading(false);
          }
        });
    }, delay);

    return () => {
      ignore = true;
      clearTimeout(timer);
    };
  }, [currentCompany, search]);

  const handleOpenCreateForm = () => {
    setEditingCustomer(null);
    setName('');
    setEmail('');
    setPhone('');
    setAddress('');
    setGstNumber('');
    setError('');
    setShowForm(true);
  };

  const handleOpenEditForm = (cust) => {
    setEditingCustomer(cust);
    setName(cust.name || '');
    setEmail(cust.email || '');
    setPhone(cust.phone || '');
    setAddress(cust.address || '');
    setGstNumber(cust.gst_number || '');
    setError('');
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingCustomer(null);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!name.trim() || !email.trim() || !phone.trim() || !address.trim()) {
      setError('Please fill in all required fields.');
      return;
    }

    setFormLoading(true);
    try {
      const payload = {
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        address: address.trim(),
        gst_number: gstNumber.trim() || null,
      };

      if (editingCustomer) {
        await updateCustomer(editingCustomer.id, payload);
        setSuccess('Customer updated successfully!');
      } else {
        await createCustomer(payload);
        setSuccess('Customer created successfully!');
      }

      handleCloseForm();
      fetchCustomers(search);
    } catch (err) {
      setError(err.message || 'Operation failed.');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteCustomer = async (cust) => {
    const confirmed = window.confirm(`Are you sure you want to delete customer "${cust.name}"?`);
    if (!confirmed) return;

    setError('');
    setSuccess('');
    setDeletingId(cust.id);

    try {
      await deleteCustomer(cust.id);
      setSuccess(`Customer "${cust.name}" deleted successfully.`);
      fetchCustomers(search);
    } catch (err) {
      setError(err.message || 'Failed to delete customer.');
    } finally {
      setDeletingId(null);
    }
  };

  if (!currentCompany) {
    return (
      <CompanyRequiredState
        message="You need to create a company profile before you can manage clients."
        onNavigateToCreateCompany={onNavigateToCreateCompany}
      />
    );
  }

  return (
    <div className="customers-module">
      {/* Module Header */}
      <div className="module-header-flex">
        <div>
          <h2 className="module-title">Customers & Clients</h2>
          <p className="module-subtitle">
            Manage client profiles, contacts, and GST info for {currentCompany.name}
          </p>
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={handleOpenCreateForm}
        >
          + Add Customer
        </button>
      </div>

      {/* Notifications */}
      {success && (
        <div className="dashboard-alert success">
          <span>{success}</span>
          <button
            type="button"
            className="alert-close"
            onClick={() => setSuccess('')}
          >
            ×
          </button>
        </div>
      )}

      {error && (
        <div className="dashboard-alert error">
          <span>{error}</span>
          <button
            type="button"
            className="alert-close"
            onClick={() => setError('')}
          >
            ×
          </button>
        </div>
      )}

      {/* Search Input Bar */}
      <div className="search-bar-wrap">
        <input
          type="text"
          className="search-input"
          placeholder="Search customers by name, email, phone, or GST number..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && (
          <button
            type="button"
            className="search-clear"
            onClick={() => setSearch('')}
          >
            Clear
          </button>
        )}
      </div>

      {/* Customer Create / Edit Form Card */}
      {showForm && (
        <section className="card">
          <div className="card-header-flex">
            <div>
              <h3 className="card-title">
                {editingCustomer ? 'Edit Customer' : 'Add New Customer'}
              </h3>
              <p className="card-subtitle">
                {editingCustomer
                  ? 'Update customer contact or tax information.'
                  : 'Enter customer details to add them to your client directory.'}
              </p>
            </div>
            <button
              type="button"
              className="link-button"
              onClick={handleCloseForm}
            >
              Cancel
            </button>
          </div>

          <form onSubmit={handleFormSubmit} className="customer-form">
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="cust-name">Customer / Business Name *</label>
                <input
                  id="cust-name"
                  type="text"
                  placeholder="Acme Corp"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="cust-email">Email Address *</label>
                <input
                  id="cust-email"
                  type="email"
                  placeholder="billing@acmecorp.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="cust-phone">Phone Number *</label>
                <input
                  id="cust-phone"
                  type="text"
                  placeholder="+91 98765 43210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="cust-gst">GST Number (Optional)</label>
                <input
                  id="cust-gst"
                  type="text"
                  placeholder="29AAAAA0000A1Z5"
                  value={gstNumber}
                  onChange={(e) => setGstNumber(e.target.value)}
                  disabled={formLoading}
                />
              </div>

              <div className="form-group full-width">
                <label htmlFor="cust-address">Billing Address *</label>
                <textarea
                  id="cust-address"
                  rows="3"
                  placeholder="Suite 500, Cyber Tower, Bangalore, Karnataka..."
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>
            </div>

            <div className="form-actions">
              <button
                type="submit"
                className="btn-primary"
                disabled={formLoading}
              >
                {formLoading
                  ? 'Saving...'
                  : editingCustomer
                  ? 'Save Changes'
                  : 'Create Customer'}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleCloseForm}
                disabled={formLoading}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      {/* Customers Data Table / List */}
      {loading ? (
        <div className="loading-spinner">Loading customers...</div>
      ) : customers.length === 0 ? (
        <div className="card empty-state-box">
          {search ? (
            <>
              <h4>No customers match your search</h4>
              <p>Try searching with another keyword or clear the search filter.</p>
              <button
                type="button"
                className="btn-secondary btn-small"
                onClick={() => setSearch('')}
              >
                Clear Search
              </button>
            </>
          ) : (
            <>
              <h4>No customers added yet</h4>
              <p>Add your first customer to get started with creating invoices.</p>
              <button
                type="button"
                className="btn-primary btn-small"
                onClick={handleOpenCreateForm}
              >
                + Add Customer
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="table-responsive">
          <table className="customers-table">
            <thead>
              <tr>
                <th>Customer Name</th>
                <th>Contact</th>
                <th>Phone</th>
                <th>GST Number</th>
                <th>Address</th>
                <th className="th-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((cust) => (
                <tr key={cust.id}>
                  <td>
                    <span className="customer-name-cell">{cust.name}</span>
                  </td>
                  <td>
                    <a
                      href={`mailto:${cust.email}`}
                      className="email-link"
                    >
                      {cust.email}
                    </a>
                  </td>
                  <td>{cust.phone}</td>
                  <td>
                    {cust.gst_number ? (
                      <span className="gst-tag">{cust.gst_number}</span>
                    ) : (
                      <span className="text-muted-dash">—</span>
                    )}
                  </td>
                  <td className="address-cell" title={cust.address}>
                    {cust.address}
                  </td>
                  <td className="actions-cell">
                    <button
                      type="button"
                      className="btn-secondary btn-small"
                      onClick={() => handleOpenEditForm(cust)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn-danger-outline"
                      onClick={() => handleDeleteCustomer(cust)}
                      disabled={deletingId === cust.id}
                    >
                      {deletingId === cust.id ? '...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Customers;