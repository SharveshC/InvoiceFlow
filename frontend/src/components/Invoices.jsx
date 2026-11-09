import { useState, useEffect, useCallback } from 'react';
import {
  getInvoices,
  getInvoice,
  createInvoice,
  updateInvoice,
  cancelInvoice,
  downloadInvoicePdf,
  getCustomers,
  getProducts,
} from '../services/api';
import CompanyRequiredState from './CompanyRequiredState';

function Invoices({ currentCompany, onNavigateToCreateCompany }) {
  // Navigation & View Mode: 'list' | 'create' | 'edit' | 'details'
  const [viewMode, setViewMode] = useState('list');
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Dropdown options
  const [availableCustomers, setAvailableCustomers] = useState([]);
  const [availableProducts, setAvailableProducts] = useState([]);

  // Form State (Create / Edit)
  const [editingInvoiceId, setEditingInvoiceId] = useState(null);
  const [customerId, setCustomerId] = useState('');
  const [invoiceNumber, setInvoiceNumber] = useState('');
  const [issueDate, setIssueDate] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [discount, setDiscount] = useState('0');
  const [notes, setNotes] = useState('');
  const [items, setItems] = useState([
    { product: '', quantity: '1', unit_price: '0.00', tax: '0.00' },
  ]);
  const [formLoading, setFormLoading] = useState(false);

  // Detail View State
  const [detailsData, setDetailsData] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  // Helper: Format today and default due date (15 days out)
  const getDefaultDates = () => {
    const today = new Date();
    const due = new Date();
    due.setDate(today.getDate() + 15);

    const formatDate = (d) => d.toISOString().split('T')[0];
    return {
      issue: formatDate(today),
      due: formatDate(due),
    };
  };

  // Fetch Invoices list
  const fetchInvoices = useCallback(async () => {
    if (!currentCompany) return;
    setLoading(true);
    try {
      const data = await getInvoices(search, statusFilter);
      setInvoices(data);
    } catch (err) {
      setError(err.message || 'Failed to load invoices.');
    } finally {
      setLoading(false);
    }
  }, [currentCompany, search, statusFilter]);

  // Load Invoices when company, search, or status filter changes
  useEffect(() => {
    let ignore = false;
    if (!currentCompany) return;

    getInvoices(search, statusFilter)
      .then((data) => {
        if (!ignore) {
          setInvoices(data);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(err.message || 'Failed to load invoices.');
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoading(false);
        }
      });

    return () => {
      ignore = true;
    };
  }, [currentCompany, search, statusFilter]);

  // Load dropdown resources (Customers & Products) for form
  const loadFormResources = async () => {
    try {
      const [custs, prods] = await Promise.all([
        getCustomers(),
        getProducts(),
      ]);
      setAvailableCustomers(custs);
      setAvailableProducts(prods);
    } catch (err) {
      console.error('Failed to load form resources:', err);
    }
  };

  // Switch to Create Invoice Form
  const handleOpenCreate = async () => {
    setError('');
    setSuccess('');
    const dates = getDefaultDates();
    setEditingInvoiceId(null);
    setCustomerId('');
    setInvoiceNumber(`INV-${String(invoices.length + 1).padStart(4, '0')}`);
    setIssueDate(dates.issue);
    setDueDate(dates.due);
    setDiscount('0');
    setNotes('');
    setItems([{ product: '', quantity: '1', unit_price: '0.00', tax: '0.00' }]);
    setViewMode('create');
    await loadFormResources();
  };

  // Switch to Edit Invoice Form
  const handleOpenEdit = async (inv) => {
    setError('');
    setSuccess('');
    setFormLoading(true);
    try {
      await loadFormResources();
      const detail = await getInvoice(inv.id);
      const invoiceData = detail.invoice;

      if (invoiceData.status === 'PAID' || invoiceData.status === 'CANCELLED') {
        setError(`Cannot edit an invoice that is already ${invoiceData.status.toLowerCase()}.`);
        return;
      }
      if (detail.payments && detail.payments.length > 0) {
        setError('Cannot edit an invoice that has recorded payments.');
        return;
      }

      setEditingInvoiceId(invoiceData.id);
      setCustomerId(String(invoiceData.customer));
      setInvoiceNumber(invoiceData.invoice_number);
      setIssueDate(invoiceData.issue_date);
      setDueDate(invoiceData.due_date);
      setDiscount(String(invoiceData.discount_amount || '0'));
      setNotes(invoiceData.notes || '');

      const loadedItems = (invoiceData.items || []).map((it) => ({
        product: String(it.product),
        quantity: String(it.quantity),
        unit_price: String(it.unit_price),
        tax: String(it.tax || '0'),
      }));

      setItems(
        loadedItems.length > 0
          ? loadedItems
          : [{ product: '', quantity: '1', unit_price: '0.00', tax: '0.00' }]
      );

      setViewMode('edit');
    } catch (err) {
      setError(err.message || 'Failed to open invoice for editing.');
    } finally {
      setFormLoading(false);
    }
  };

  // Switch to Invoice Details View
  const handleOpenDetails = async (invId) => {
    setError('');
    setSuccess('');
    setDetailsLoading(true);
    setViewMode('details');
    try {
      const data = await getInvoice(invId);
      setDetailsData(data);
    } catch (err) {
      setError(err.message || 'Failed to load invoice details.');
    } finally {
      setDetailsLoading(false);
    }
  };

  // Back to list view
  const handleBackToList = () => {
    setViewMode('list');
    setDetailsData(null);
    setEditingInvoiceId(null);
    fetchInvoices();
  };

  // Add line item row
  const handleAddItem = () => {
    setItems((prev) => [
      ...prev,
      { product: '', quantity: '1', unit_price: '0.00', tax: '0.00' },
    ]);
  };

  // Remove line item row
  const handleRemoveItem = (index) => {
    if (items.length <= 1) {
      setError('Invoice must have at least one line item.');
      return;
    }
    setItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  // When product dropdown changes in an item row
  const handleProductChange = (index, prodId) => {
    const selectedProd = availableProducts.find((p) => String(p.id) === String(prodId));
    setItems((prev) =>
      prev.map((item, idx) => {
        if (idx !== index) return item;
        if (!selectedProd) {
          return { ...item, product: '' };
        }
        return {
          ...item,
          product: String(selectedProd.id),
          unit_price: String(selectedProd.price || '0.00'),
          tax: String(selectedProd.tax || '0.00'),
        };
      })
    );
  };

  // Update item field (quantity, unit_price, tax)
  const handleItemFieldChange = (index, field, value) => {
    setItems((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, [field]: value } : item))
    );
  };

  // Live calculation of item line total for display
  const getItemLineTotal = (item) => {
    const qty = parseFloat(item.quantity) || 0;
    const price = parseFloat(item.unit_price) || 0;
    const taxRate = parseFloat(item.tax) || 0;
    const sub = qty * price;
    const lineTax = (sub * taxRate) / 100;
    return sub + lineTax;
  };

  // Live calculation of totals for form display
  const calculateTotals = () => {
    let subtotal = 0;
    let taxAmount = 0;

    items.forEach((item) => {
      const qty = parseFloat(item.quantity) || 0;
      const price = parseFloat(item.unit_price) || 0;
      const taxRate = parseFloat(item.tax) || 0;
      const lineSub = qty * price;
      const lineTax = (lineSub * taxRate) / 100;
      subtotal += lineSub;
      taxAmount += lineTax;
    });

    const disc = parseFloat(discount) || 0;
    const grandTotal = Math.max(subtotal + taxAmount - disc, 0);

    return {
      subtotal,
      taxAmount,
      discount: disc,
      grandTotal,
    };
  };

  const totals = calculateTotals();

  // Submit Create or Edit Form
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!invoiceNumber.trim()) {
      setError('Invoice number is required.');
      return;
    }
    if (!customerId) {
      setError('Please select a customer.');
      return;
    }
    if (!issueDate || !dueDate) {
      setError('Please select valid issue and due dates.');
      return;
    }
    if (new Date(dueDate) < new Date(issueDate)) {
      setError('Due date cannot be before the issue date.');
      return;
    }
    if (items.length === 0) {
      setError('Please add at least one line item.');
      return;
    }

    // Validate each item
    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (!it.product) {
        setError(`Please select a product for item #${i + 1}.`);
        return;
      }
      const qty = parseFloat(it.quantity);
      const price = parseFloat(it.unit_price);
      const taxRate = parseFloat(it.tax);
      if (isNaN(qty) || qty <= 0) {
        setError(`Item #${i + 1}: Quantity must be greater than zero.`);
        return;
      }
      if (isNaN(price) || price < 0) {
        setError(`Item #${i + 1}: Unit price cannot be negative.`);
        return;
      }
      if (isNaN(taxRate) || taxRate < 0) {
        setError(`Item #${i + 1}: Tax rate cannot be negative.`);
        return;
      }
    }

    const disc = parseFloat(discount);
    if (isNaN(disc) || disc < 0) {
      setError('Discount amount cannot be negative.');
      return;
    }

    const payload = {
      invoice_number: invoiceNumber.trim(),
      customer: parseInt(customerId, 10),
      issue_date: issueDate,
      due_date: dueDate,
      discount: disc.toFixed(2),
      notes: notes.trim(),
      items: items.map((it) => ({
        product: parseInt(it.product, 10),
        quantity: parseFloat(it.quantity).toFixed(2),
        unit_price: parseFloat(it.unit_price).toFixed(2),
        tax: parseFloat(it.tax || '0').toFixed(2),
      })),
    };

    setFormLoading(true);
    try {
      if (editingInvoiceId) {
        await updateInvoice(editingInvoiceId, payload);
        setSuccess('Invoice updated successfully!');
      } else {
        await createInvoice(payload);
        setSuccess('Invoice created successfully!');
      }
      handleBackToList();
    } catch (err) {
      setError(err.message || 'Failed to save invoice.');
    } finally {
      setFormLoading(false);
    }
  };

  // Cancel invoice action
  const handleCancel = async (invId) => {
    const confirmed = window.confirm('Are you sure you want to cancel this invoice?');
    if (!confirmed) return;

    setError('');
    setSuccess('');
    setCancelling(true);
    try {
      await cancelInvoice(invId);
      setSuccess('Invoice cancelled successfully.');
      if (viewMode === 'details') {
        const updated = await getInvoice(invId);
        setDetailsData(updated);
      } else {
        fetchInvoices();
      }
    } catch (err) {
      setError(err.message || 'Failed to cancel invoice.');
    } finally {
      setCancelling(false);
    }
  };

  // Download PDF handler
  const handleDownload = async (invId, invNumber) => {
    setPdfLoading(true);
    try {
      await downloadInvoicePdf(invId, invNumber);
    } catch (err) {
      setError(err.message || 'Failed to download PDF.');
    } finally {
      setPdfLoading(false);
    }
  };

  // Format currency helper
  const formatCurrency = (val) => {
    const num = parseFloat(val) || 0;
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // Render Status Badge helper
  const renderStatusBadge = (status) => {
    const st = (status || 'DRAFT').toLowerCase();
    return <span className={`status-badge status-${st}`}>{status}</span>;
  };

  if (!currentCompany) {
    return (
      <CompanyRequiredState
        message="You need to create a company profile before you can create and manage invoices."
        onNavigateToCreateCompany={onNavigateToCreateCompany}
      />
    );
  }

  // ==========================================
  // VIEW: DETAILS VIEW
  // ==========================================
  if (viewMode === 'details') {
    if (detailsLoading || !detailsData) {
      return <div className="loading-spinner">Loading invoice details...</div>;
    }

    const { invoice, customer, payments = [], paid_amount = '0.00', remaining_amount = '0.00' } = detailsData;
    const canCancel = invoice.status !== 'PAID' && invoice.status !== 'CANCELLED';
    const canEdit = invoice.status !== 'PAID' && invoice.status !== 'CANCELLED' && payments.length === 0;

    return (
      <div className="invoices-module">
        <div className="module-header-flex">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h2 className="module-title">Invoice {invoice.invoice_number}</h2>
              {renderStatusBadge(invoice.status)}
            </div>
            <p className="module-subtitle">
              Issued for {customer?.name || invoice.customer_name} on {invoice.issue_date}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn-secondary btn-small"
              onClick={handleBackToList}
            >
              ← Back to Invoices
            </button>

            <button
              type="button"
              className="btn-primary btn-small"
              onClick={() => handleDownload(invoice.id, invoice.invoice_number)}
              disabled={pdfLoading}
            >
              {pdfLoading ? 'Downloading...' : 'Download PDF'}
            </button>

            {canEdit && (
              <button
                type="button"
                className="btn-secondary btn-small"
                onClick={() => handleOpenEdit(invoice)}
              >
                Edit Invoice
              </button>
            )}

            {canCancel && (
              <button
                type="button"
                className="btn-danger-outline"
                onClick={() => handleCancel(invoice.id)}
                disabled={cancelling}
              >
                {cancelling ? 'Cancelling...' : 'Cancel Invoice'}
              </button>
            )}
          </div>
        </div>

        {/* Notifications */}
        {success && (
          <div className="dashboard-alert success">
            <span>{success}</span>
            <button type="button" className="alert-close" onClick={() => setSuccess('')}>×</button>
          </div>
        )}
        {error && (
          <div className="dashboard-alert error">
            <span>{error}</span>
            <button type="button" className="alert-close" onClick={() => setError('')}>×</button>
          </div>
        )}

        {/* Info Grid: Invoice Info & Customer Details */}
        <div className="form-grid" style={{ marginBottom: '20px' }}>
          <section className="card" style={{ marginBottom: 0 }}>
            <h3 className="card-title">Invoice Information</h3>
            <div className="company-details-grid" style={{ marginTop: '12px', paddingTop: '12px' }}>
              <div className="detail-item">
                <span className="detail-label">Invoice Number</span>
                <span className="detail-value">{invoice.invoice_number}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Status</span>
                <span className="detail-value">{invoice.status}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Issue Date</span>
                <span className="detail-value">{invoice.issue_date}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Due Date</span>
                <span className="detail-value">{invoice.due_date}</span>
              </div>
            </div>
          </section>

          <section className="card" style={{ marginBottom: 0 }}>
            <h3 className="card-title">Customer Information</h3>
            <div className="company-details-grid" style={{ marginTop: '12px', paddingTop: '12px' }}>
              <div className="detail-item">
                <span className="detail-label">Client Name</span>
                <span className="detail-value">{customer?.name || invoice.customer_name}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Email</span>
                <span className="detail-value">{customer?.email || '—'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Phone</span>
                <span className="detail-value">{customer?.phone || '—'}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">GST Number</span>
                <span className="detail-value">{customer?.gst_number || '—'}</span>
              </div>
            </div>
          </section>
        </div>

        {/* Line Items Table */}
        <section className="card">
          <h3 className="card-title" style={{ marginBottom: '16px' }}>Invoice Items</h3>
          <div className="table-responsive" style={{ border: 'none', marginBottom: '16px' }}>
            <table className="invoices-table">
              <thead>
                <tr>
                  <th>Product / Service</th>
                  <th>Quantity</th>
                  <th>Unit Price</th>
                  <th>Tax</th>
                  <th style={{ textAlign: 'right' }}>Line Total</th>
                </tr>
              </thead>
              <tbody>
                {(invoice.items || []).map((it) => (
                  <tr key={it.id}>
                    <td>
                      <span className="customer-name-cell">{it.product_name}</span>
                    </td>
                    <td>{it.quantity}</td>
                    <td>{formatCurrency(it.unit_price)}</td>
                    <td>
                      <span className="tax-tag">{it.tax}%</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="price-tag">{formatCurrency(it.line_total)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Totals Summary */}
          <div className="invoice-totals-box">
            <div className="invoice-total-row">
              <span className="detail-label">Subtotal</span>
              <span className="detail-value">{formatCurrency(invoice.subtotal)}</span>
            </div>
            <div className="invoice-total-row">
              <span className="detail-label">Tax Amount</span>
              <span className="detail-value">{formatCurrency(invoice.tax_amount)}</span>
            </div>
            <div className="invoice-total-row">
              <span className="detail-label">Discount</span>
              <span className="detail-value">-{formatCurrency(invoice.discount_amount)}</span>
            </div>
            <div className="invoice-total-row grand-total-row">
              <span className="item-company-name">Total</span>
              <span className="grand-total-val">{formatCurrency(invoice.total)}</span>
            </div>
          </div>
        </section>

        {/* Payment Summary */}
        <section className="card">
          <h3 className="card-title">Payment Summary</h3>
          <div className="company-details-grid" style={{ marginTop: '12px', paddingTop: '12px' }}>
            <div className="detail-item">
              <span className="detail-label">Total Amount</span>
              <span className="detail-value">{formatCurrency(invoice.total)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Amount Paid</span>
              <span className="detail-value" style={{ color: '#4ade80' }}>
                {formatCurrency(paid_amount)}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Remaining Balance</span>
              <span className="detail-value" style={{ color: '#f87171' }}>
                {formatCurrency(remaining_amount)}
              </span>
            </div>
          </div>

          {/* Payment History Table */}
          {payments.length > 0 && (
            <div style={{ marginTop: '20px' }}>
              <h4 style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
                Payment History ({payments.length})
              </h4>
              <div className="table-responsive">
                <table className="invoices-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Method</th>
                      <th>Notes</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((p) => (
                      <tr key={p.id}>
                        <td>{p.payment_date}</td>
                        <td>{p.payment_method}</td>
                        <td>{p.notes || '—'}</td>
                        <td style={{ textAlign: 'right' }}>
                          <span className="price-tag" style={{ color: '#4ade80' }}>
                            {formatCurrency(p.amount)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        {invoice.notes && (
          <section className="card">
            <h3 className="card-title">Notes</h3>
            <p style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              {invoice.notes}
            </p>
          </section>
        )}
      </div>
    );
  }

  // ==========================================
  // VIEW: CREATE / EDIT FORM VIEW
  // ==========================================
  if (viewMode === 'create' || viewMode === 'edit') {
    return (
      <div className="invoices-module">
        <div className="module-header-flex">
          <div>
            <h2 className="module-title">
              {viewMode === 'edit' ? `Edit Invoice ${invoiceNumber}` : 'Create New Invoice'}
            </h2>
            <p className="module-subtitle">
              {viewMode === 'edit'
                ? 'Update client, line items, and notes before saving.'
                : 'Select a customer and add product items to generate an invoice.'}
            </p>
          </div>

          <button
            type="button"
            className="btn-secondary btn-small"
            onClick={handleBackToList}
            disabled={formLoading}
          >
            ← Cancel & Back
          </button>
        </div>

        {/* Notifications */}
        {error && (
          <div className="dashboard-alert error">
            <span>{error}</span>
            <button type="button" className="alert-close" onClick={() => setError('')}>×</button>
          </div>
        )}

        <form onSubmit={handleFormSubmit}>
          {/* General Information Card */}
          <section className="card">
            <h3 className="card-title" style={{ marginBottom: '16px' }}>Invoice Details</h3>
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="inv-customer">Select Customer *</label>
                <select
                  id="inv-customer"
                  value={customerId}
                  onChange={(e) => setCustomerId(e.target.value)}
                  disabled={formLoading}
                  required
                >
                  <option value="">-- Choose Customer --</option>
                  {availableCustomers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} {c.gst_number ? `(${c.gst_number})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="inv-number">Invoice Number *</label>
                <input
                  id="inv-number"
                  type="text"
                  placeholder="INV-0001"
                  value={invoiceNumber}
                  onChange={(e) => setInvoiceNumber(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="inv-issue-date">Issue Date *</label>
                <input
                  id="inv-issue-date"
                  type="date"
                  value={issueDate}
                  onChange={(e) => setIssueDate(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="inv-due-date">Due Date *</label>
                <input
                  id="inv-due-date"
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>
            </div>
          </section>

          {/* Line Items Card */}
          <section className="card">
            <div className="card-header-flex">
              <div>
                <h3 className="card-title">Invoice Items</h3>
                <p className="card-subtitle">Add products and services to include in this invoice.</p>
              </div>
              <button
                type="button"
                className="btn-secondary btn-small"
                onClick={handleAddItem}
                disabled={formLoading}
              >
                + Add Item
              </button>
            </div>

            <div className="invoice-items-list" style={{ marginTop: '16px' }}>
              {items.map((item, idx) => {
                const lineTotal = getItemLineTotal(item);

                return (
                  <div key={idx} className="invoice-item-row-card">
                    <div className="item-row-grid">
                      <div className="form-group item-prod-col">
                        <label>Product / Service *</label>
                        <select
                          value={item.product}
                          onChange={(e) => handleProductChange(idx, e.target.value)}
                          disabled={formLoading}
                          required
                        >
                          <option value="">-- Choose Product --</option>
                          {availableProducts.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name} (₹{p.price})
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="form-group item-qty-col">
                        <label>Quantity *</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0.01"
                          value={item.quantity}
                          onChange={(e) => handleItemFieldChange(idx, 'quantity', e.target.value)}
                          disabled={formLoading}
                          required
                        />
                      </div>

                      <div className="form-group item-price-col">
                        <label>Unit Price (₹) *</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={item.unit_price}
                          onChange={(e) => handleItemFieldChange(idx, 'unit_price', e.target.value)}
                          disabled={formLoading}
                          required
                        />
                      </div>

                      <div className="form-group item-tax-col">
                        <label>Tax (%)</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={item.tax}
                          onChange={(e) => handleItemFieldChange(idx, 'tax', e.target.value)}
                          disabled={formLoading}
                        />
                      </div>

                      <div className="item-total-col">
                        <span className="detail-label">Line Total</span>
                        <span className="price-tag" style={{ display: 'block', marginTop: '8px' }}>
                          {formatCurrency(lineTotal)}
                        </span>
                      </div>

                      <div className="item-remove-col">
                        <button
                          type="button"
                          className="btn-danger-outline btn-small"
                          onClick={() => handleRemoveItem(idx)}
                          disabled={formLoading || items.length <= 1}
                          title="Remove item"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Discount & Totals Summary */}
            <div className="form-grid" style={{ marginTop: '24px', alignItems: 'flex-start' }}>
              <div className="form-group">
                <label htmlFor="inv-discount">Invoice Discount Amount (₹)</label>
                <input
                  id="inv-discount"
                  type="number"
                  step="0.01"
                  min="0"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                  disabled={formLoading}
                />
              </div>

              <div className="invoice-totals-box">
                <div className="invoice-total-row">
                  <span className="detail-label">Subtotal</span>
                  <span className="detail-value">{formatCurrency(totals.subtotal)}</span>
                </div>
                <div className="invoice-total-row">
                  <span className="detail-label">Tax Amount</span>
                  <span className="detail-value">{formatCurrency(totals.taxAmount)}</span>
                </div>
                <div className="invoice-total-row">
                  <span className="detail-label">Discount</span>
                  <span className="detail-value">-{formatCurrency(totals.discount)}</span>
                </div>
                <div className="invoice-total-row grand-total-row">
                  <span className="item-company-name">Grand Total</span>
                  <span className="grand-total-val">{formatCurrency(totals.grandTotal)}</span>
                </div>
              </div>
            </div>
          </section>

          {/* Notes Card */}
          <section className="card">
            <div className="form-group full-width">
              <label htmlFor="inv-notes">Notes / Payment Terms (Optional)</label>
              <textarea
                id="inv-notes"
                rows="3"
                placeholder="Payment terms: Net 15 days. Bank transfer details..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={formLoading}
              />
            </div>

            <div className="form-actions" style={{ marginTop: '20px' }}>
              <button
                type="submit"
                className="btn-primary"
                disabled={formLoading}
              >
                {formLoading
                  ? 'Saving...'
                  : viewMode === 'edit'
                  ? 'Save Changes'
                  : 'Create Invoice'}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleBackToList}
                disabled={formLoading}
              >
                Cancel
              </button>
            </div>
          </section>
        </form>
      </div>
    );
  }

  // ==========================================
  // VIEW: LIST VIEW (DEFAULT)
  // ==========================================
  return (
    <div className="invoices-module">
      {/* Header */}
      <div className="module-header-flex">
        <div>
          <h2 className="module-title">Invoices</h2>
          <p className="module-subtitle">
            Manage billing, dispatch, and track payments for {currentCompany.name}
          </p>
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={handleOpenCreate}
        >
          + Create Invoice
        </button>
      </div>

      {/* Notifications */}
      {success && (
        <div className="dashboard-alert success">
          <span>{success}</span>
          <button type="button" className="alert-close" onClick={() => setSuccess('')}>×</button>
        </div>
      )}
      {error && (
        <div className="dashboard-alert error">
          <span>{error}</span>
          <button type="button" className="alert-close" onClick={() => setError('')}>×</button>
        </div>
      )}

      {/* Filter & Search Bar */}
      <div className="search-bar-wrap" style={{ display: 'flex', gap: '12px' }}>
        <input
          type="text"
          className="search-input"
          style={{ flex: 1 }}
          placeholder="Search by invoice number or customer name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="status-select-filter"
        >
          <option value="ALL">All Statuses</option>
          <option value="SENT">Sent</option>
          <option value="PAID">Paid</option>
          <option value="OVERDUE">Overdue</option>
          <option value="CANCELLED">Cancelled</option>
          <option value="DRAFT">Draft</option>
        </select>
      </div>

      {/* Data Table */}
      {loading ? (
        <div className="loading-spinner">Loading invoices...</div>
      ) : invoices.length === 0 ? (
        <div className="card empty-state-box">
          {search || statusFilter !== 'ALL' ? (
            <>
              <h4>No invoices match your filter</h4>
              <p>Try searching with another keyword or reset the status filter.</p>
              <button
                type="button"
                className="btn-secondary btn-small"
                onClick={() => {
                  setSearch('');
                  setStatusFilter('ALL');
                }}
              >
                Reset Filters
              </button>
            </>
          ) : (
            <>
              <h4>No invoices created yet</h4>
              <p>Create your first invoice to dispatch to your clients.</p>
              <button
                type="button"
                className="btn-primary btn-small"
                onClick={handleOpenCreate}
              >
                + Create Invoice
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="table-responsive">
          <table className="invoices-table">
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Customer</th>
                <th>Issue Date</th>
                <th>Due Date</th>
                <th>Total</th>
                <th>Status</th>
                <th className="th-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => {
                const canEdit = inv.status !== 'PAID' && inv.status !== 'CANCELLED';

                return (
                  <tr key={inv.id}>
                    <td>
                      <span
                        className="customer-name-cell link-cell"
                        onClick={() => handleOpenDetails(inv.id)}
                      >
                        {inv.invoice_number}
                      </span>
                    </td>
                    <td>{inv.customer_name}</td>
                    <td>{inv.issue_date}</td>
                    <td>{inv.due_date}</td>
                    <td>
                      <span className="price-tag">{formatCurrency(inv.total)}</span>
                    </td>
                    <td>{renderStatusBadge(inv.status)}</td>
                    <td className="actions-cell">
                      <button
                        type="button"
                        className="btn-secondary btn-small"
                        onClick={() => handleOpenDetails(inv.id)}
                      >
                        View
                      </button>
                      {canEdit && (
                        <button
                          type="button"
                          className="btn-secondary btn-small"
                          onClick={() => handleOpenEdit(inv)}
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default Invoices;

