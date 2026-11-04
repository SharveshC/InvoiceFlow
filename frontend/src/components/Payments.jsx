import { useState, useEffect, useCallback } from 'react';
import {
  getPayments,
  recordPayment,
  getInvoices,
} from '../services/api';

function Payments({ currentCompany }) {
  // Payments list & stats
  const [payments, setPayments] = useState([]);
  const [stats, setStats] = useState({
    total_received: '0.00',
    this_month: '0.00',
    payment_count: 0,
  });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [methodFilter, setMethodFilter] = useState('ALL');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Record Payment Modal / Card
  const [showRecordModal, setShowRecordModal] = useState(false);
  const [availableInvoices, setAvailableInvoices] = useState([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState('');
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('UPI');
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState('');

  // Read-only Payment Details View
  const [viewingPayment, setViewingPayment] = useState(null);

  // Currency Formatter
  const formatCurrency = (val) => {
    const num = parseFloat(val) || 0;
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // Fetch payments and active company statistics
  const fetchPayments = useCallback(async () => {
    if (!currentCompany) return;
    setLoading(true);
    try {
      const data = await getPayments(search, methodFilter);
      setPayments(data.payments || []);
      if (data.stats) {
        setStats(data.stats);
      }
    } catch (err) {
      setError(err.message || 'Failed to load payments.');
    } finally {
      setLoading(false);
    }
  }, [currentCompany, search, methodFilter]);

  // Synchronize on company, search, or filter changes with cleanup (debounced by 300ms on search)
  useEffect(() => {
    let ignore = false;
    if (!currentCompany) return;

    const delay = search ? 300 : 0;
    const timer = setTimeout(() => {
      getPayments(search, methodFilter)
        .then((data) => {
          if (!ignore) {
            setPayments(data.payments || []);
            if (data.stats) {
              setStats(data.stats);
            }
          }
        })
        .catch((err) => {
          if (!ignore) {
            setError(err.message || 'Failed to load payments.');
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
  }, [currentCompany, search, methodFilter]);

  // Load unpaid/partially-paid invoices for active company
  const handleOpenRecordModal = async () => {
    setFormError('');
    setSelectedInvoiceId('');
    setAmount('');
    setPaymentMethod('UPI');
    setPaymentDate(new Date().toISOString().split('T')[0]);
    setNotes('');
    setShowRecordModal(true);
    setInvoicesLoading(true);

    try {
      const invs = await getInvoices();
      // Filter out CANCELLED invoices and already fully paid invoices
      const payableInvoices = invs.filter((inv) => {
        if (inv.status === 'CANCELLED') return false;
        const rem = parseFloat(inv.remaining_amount);
        if (!isNaN(rem) && rem <= 0) return false;
        if (inv.status === 'PAID') return false;
        return true;
      });
      setAvailableInvoices(payableInvoices);
      if (payableInvoices.length > 0) {
        setSelectedInvoiceId(String(payableInvoices[0].id));
      }
    } catch (err) {
      setFormError(err.message || 'Failed to load invoices.');
    } finally {
      setInvoicesLoading(false);
    }
  };

  // Currently selected invoice in the record modal
  const selectedInvoice = availableInvoices.find(
    (inv) => String(inv.id) === String(selectedInvoiceId)
  );

  // Quick fill remaining balance
  const handleFillFullBalance = () => {
    if (!selectedInvoice) return;
    const rem = selectedInvoice.remaining_amount || selectedInvoice.total || '0.00';
    setAmount(String(rem));
  };

  // Record payment form submit
  const handleSubmitPayment = async (e) => {
    e.preventDefault();
    setFormError('');

    if (!selectedInvoiceId) {
      setFormError('Please select an invoice.');
      return;
    }

    const payAmount = parseFloat(amount);
    if (isNaN(payAmount) || payAmount <= 0) {
      setFormError('Please enter a valid payment amount greater than zero.');
      return;
    }

    if (selectedInvoice) {
      const maxRemaining = parseFloat(selectedInvoice.remaining_amount || selectedInvoice.total);
      if (payAmount > maxRemaining) {
        setFormError(`Payment cannot exceed the remaining balance of ${formatCurrency(maxRemaining)}.`);
        return;
      }
    }

    if (!paymentDate) {
      setFormError('Please select a valid payment date.');
      return;
    }

    setFormLoading(true);
    try {
      const result = await recordPayment({
        invoice: selectedInvoiceId,
        amount: amount.trim(),
        payment_method: paymentMethod,
        payment_date: paymentDate,
        notes: notes.trim() || undefined,
      });

      setShowRecordModal(false);
      setSuccess(
        `Payment of ${formatCurrency(amount)} recorded successfully! Invoice status is now ${result.invoice_status}.`
      );
      fetchPayments();
    } catch (err) {
      setFormError(err.message || 'Failed to record payment.');
    } finally {
      setFormLoading(false);
    }
  };

  // Helper for Payment Method badges with indicator dot
  const renderMethodBadge = (method, display) => {
    const m = (method || '').toLowerCase();
    return (
      <span className={`method-badge method-${m}`}>
        <span className="method-badge-dot" />
        {display || method}
      </span>
    );
  };

  return (
    <div className="payments-management-container">
      {/* Active Company Payment Metrics */}
      <section className="stats-grid">
        <div className="stat-card">
          <span className="stat-card-label">Total Received</span>
          <span className="stat-card-value">{formatCurrency(stats.total_received)}</span>
          <span className="stat-card-subtext">Lifetime revenue collected</span>
        </div>

        <div className="stat-card">
          <span className="stat-card-label">This Month</span>
          <span className="stat-card-value">{formatCurrency(stats.this_month)}</span>
          <span className="stat-card-subtext">Received in current calendar month</span>
        </div>

        <div className="stat-card">
          <span className="stat-card-label">Total Transactions</span>
          <span className="stat-card-value">{stats.payment_count}</span>
          <span className="stat-card-subtext">Completed payment entries</span>
        </div>
      </section>

      {/* Main Payments Card */}
      <section className="card">
        {/* Header with Title and Action */}
        <div className="card-header-flex">
          <div>
            <h2 className="card-title">Payment History</h2>
            <p className="card-subtitle">
              Audit log of transactions recorded against invoices. All payments are immutable records.
            </p>
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={handleOpenRecordModal}
          >
            + Record Payment
          </button>
        </div>

        {/* Global Success / Error Alerts */}
        {success && (
          <div className="dashboard-alert success" style={{ marginTop: '16px' }}>
            <span>{success}</span>
            <button
              type="button"
              className="alert-close"
              onClick={() => setSuccess('')}
            >
              ✕
            </button>
          </div>
        )}

        {error && (
          <div className="dashboard-alert error" style={{ marginTop: '16px' }}>
            <span>{error}</span>
            <button
              type="button"
              className="alert-close"
              onClick={() => setError('')}
            >
              ✕
            </button>
          </div>
        )}

        {/* Search & Filter Bar: Horizontally Aligned */}
        <div className="payments-controls-bar">
          <div className="payments-search-wrapper">
            <span className="payments-search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search by invoice # or customer..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="payments-search-input"
            />
          </div>

          <div className="payments-filter-group">
            <select
              value={methodFilter}
              onChange={(e) => setMethodFilter(e.target.value)}
              className="payments-filter-select"
            >
              <option value="ALL">All Methods</option>
              <option value="UPI">UPI</option>
              <option value="CASH">Cash</option>
              <option value="CARD">Card</option>
              <option value="BANK">Bank Transfer</option>
            </select>
          </div>
        </div>

        {/* Payments Table */}
        {loading ? (
          <div className="empty-state-box">
            <p>Loading payments...</p>
          </div>
        ) : payments.length === 0 ? (
          <div className="empty-state-box">
            <h4>{search || methodFilter !== 'ALL' ? 'No matching payments found' : 'No payments recorded yet'}</h4>
            <p>
              {search || methodFilter !== 'ALL'
                ? 'Try adjusting your search criteria or payment method filter.'
                : 'Record your first invoice settlement by clicking "+ Record Payment" above.'}
            </p>
          </div>
        ) : (
          <div className="table-responsive" style={{ marginTop: '8px' }}>
            <table className="payments-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Invoice #</th>
                  <th>Customer</th>
                  <th>Method</th>
                  <th>Amount Received</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {payments.map((p) => (
                  <tr key={p.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                      {p.payment_date}
                    </td>
                    <td>
                      <span className="cell-main-title" style={{ fontFamily: 'var(--font-mono)' }}>
                        {p.invoice_number}
                      </span>
                    </td>
                    <td>
                      <span className="cell-main-title">{p.customer_name || '—'}</span>
                    </td>
                    <td>{renderMethodBadge(p.payment_method, p.payment_method_display)}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: '#4ade80' }}>
                      + {formatCurrency(p.amount)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn-table-action"
                        onClick={() => setViewingPayment(p)}
                        title="View Payment Audit Details"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Record Payment Modal (Centered with Dark Blur Backdrop) */}
      {showRecordModal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !formLoading) {
              setShowRecordModal(false);
            }
          }}
        >
          <div className="modal-container" style={{ maxWidth: '540px' }}>
            <div className="modal-header">
              <div>
                <h3 className="card-title" style={{ fontSize: '17px', margin: 0 }}>Record Payment</h3>
                <p className="card-subtitle" style={{ margin: '4px 0 0 0' }}>
                  Apply a verified payment towards an open invoice.
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowRecordModal(false)}
                disabled={formLoading}
                title="Close"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitPayment}>
              <div className="modal-body">
                {formError && (
                  <div className="dashboard-alert error" style={{ marginBottom: '16px' }}>
                    <span>{formError}</span>
                  </div>
                )}

                {invoicesLoading ? (
                  <div className="empty-state-box" style={{ padding: '28px' }}>
                    <p>Loading payable invoices...</p>
                  </div>
                ) : availableInvoices.length === 0 ? (
                  <div className="empty-state-box" style={{ padding: '32px 16px' }}>
                    <h4>No unpaid invoices available</h4>
                    <p>All active invoices are either fully paid or cancelled.</p>
                  </div>
                ) : (
                  <>
                    {/* Invoice Selector */}
                    <div className="form-group" style={{ marginBottom: '16px' }}>
                      <label htmlFor="pay-invoice">Select Invoice *</label>
                      <select
                        id="pay-invoice"
                        value={selectedInvoiceId}
                        onChange={(e) => {
                          setSelectedInvoiceId(e.target.value);
                          setAmount('');
                        }}
                        disabled={formLoading}
                        required
                      >
                        {availableInvoices.map((inv) => (
                          <option key={inv.id} value={inv.id}>
                            {inv.invoice_number} — {inv.customer_name} (Balance: {formatCurrency(inv.remaining_amount || inv.total)})
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Selected Invoice Breakdown Preview */}
                    {selectedInvoice && (
                      <div className="payment-breakdown-card">
                        <div className="payment-breakdown-grid">
                          <div className="breakdown-item">
                            <span className="breakdown-label">Invoice Total</span>
                            <span className="breakdown-value">{formatCurrency(selectedInvoice.total)}</span>
                          </div>

                          <div className="breakdown-item">
                            <span className="breakdown-label">Already Paid</span>
                            <span className="breakdown-value">{formatCurrency(selectedInvoice.paid_amount || '0.00')}</span>
                          </div>

                          <div className="breakdown-item">
                            <span className="breakdown-label">Remaining Balance</span>
                            <span className="breakdown-value highlight-balance">
                              {formatCurrency(selectedInvoice.remaining_amount || selectedInvoice.total)}
                            </span>
                            <button
                              type="button"
                              className="quick-fill-btn"
                              onClick={handleFillFullBalance}
                              title="Autofill full remaining balance"
                            >
                              Pay Full Balance
                            </button>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="form-grid">
                      {/* Amount Input */}
                      <div className="form-group">
                        <label htmlFor="pay-amount">Amount (₹) *</label>
                        <input
                          id="pay-amount"
                          type="number"
                          step="0.01"
                          min="0.01"
                          placeholder="0.00"
                          value={amount}
                          onChange={(e) => setAmount(e.target.value)}
                          disabled={formLoading}
                          required
                        />
                      </div>

                      {/* Payment Method */}
                      <div className="form-group">
                        <label htmlFor="pay-method">Payment Method *</label>
                        <select
                          id="pay-method"
                          value={paymentMethod}
                          onChange={(e) => setPaymentMethod(e.target.value)}
                          disabled={formLoading}
                          required
                        >
                          <option value="UPI">UPI</option>
                          <option value="CASH">Cash</option>
                          <option value="CARD">Card</option>
                          <option value="BANK">Bank Transfer</option>
                        </select>
                      </div>
                    </div>

                    <div className="form-grid">
                      {/* Payment Date */}
                      <div className="form-group">
                        <label htmlFor="pay-date">Payment Date *</label>
                        <input
                          id="pay-date"
                          type="date"
                          value={paymentDate}
                          onChange={(e) => setPaymentDate(e.target.value)}
                          disabled={formLoading}
                          required
                        />
                      </div>

                      {/* Notes / Reference */}
                      <div className="form-group">
                        <label htmlFor="pay-notes">Reference / Notes (Optional)</label>
                        <input
                          id="pay-notes"
                          type="text"
                          placeholder="e.g. UTR / Txn #12345"
                          value={notes}
                          onChange={(e) => setNotes(e.target.value)}
                          disabled={formLoading}
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowRecordModal(false)}
                  disabled={formLoading}
                >
                  Cancel
                </button>
                {availableInvoices.length > 0 && (
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={formLoading || invoicesLoading}
                  >
                    {formLoading ? 'Recording...' : 'Record Payment'}
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

      {/* View Payment Details Modal (Centered with Dark Blur Backdrop) */}
      {viewingPayment && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setViewingPayment(null);
            }
          }}
        >
          <div className="modal-container" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <div>
                <h3 className="card-title" style={{ fontSize: '17px', margin: 0 }}>Payment #{viewingPayment.id}</h3>
                <p className="card-subtitle" style={{ margin: '4px 0 0 0' }}>
                  Verified immutable transaction record
                </p>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setViewingPayment(null)}
                title="Close"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              <div className="audit-amount-banner">
                <div>
                  <span className="audit-amount-label">Amount Received</span>
                  <div className="audit-amount-value">
                    {formatCurrency(viewingPayment.amount)}
                  </div>
                </div>
                {renderMethodBadge(viewingPayment.payment_method, viewingPayment.payment_method_display)}
              </div>

              <div className="audit-grid">
                <div className="detail-item">
                  <span className="detail-label">Invoice Number</span>
                  <span className="detail-value" style={{ fontFamily: 'var(--font-mono)' }}>
                    {viewingPayment.invoice_number}
                  </span>
                </div>

                <div className="detail-item">
                  <span className="detail-label">Customer</span>
                  <span className="detail-value">{viewingPayment.customer_name || '—'}</span>
                </div>

                <div className="detail-item">
                  <span className="detail-label">Payment Date</span>
                  <span className="detail-value" style={{ fontFamily: 'var(--font-mono)' }}>
                    {viewingPayment.payment_date}
                  </span>
                </div>

                <div className="detail-item">
                  <span className="detail-label">System Timestamp</span>
                  <span className="detail-value" style={{ fontSize: '12px' }}>
                    {viewingPayment.created_at ? new Date(viewingPayment.created_at).toLocaleString() : '—'}
                  </span>
                </div>

                <div className="detail-item full-width" style={{ gridColumn: 'span 2' }}>
                  <span className="detail-label">Reference Notes</span>
                  <span className="detail-value">{viewingPayment.notes || 'No reference note attached.'}</span>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setViewingPayment(null)}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Payments;
