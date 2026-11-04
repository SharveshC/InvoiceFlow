import { useState, useEffect, useCallback } from 'react';
import {
  getReportsSummary,
  downloadFinancialReportPdf,
} from '../services/api';

function Reports({ currentCompany }) {
  // Report data state
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pdfLoading, setPdfLoading] = useState(false);

  // Date filtering state
  const [preset, setPreset] = useState('6m');
  const [isCustom, setIsCustom] = useState(false);
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  // Currency Formatter Helper
  const formatCurrency = (val) => {
    const num = parseFloat(val) || 0;
    return '₹' + num.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // Fetch report analytics helper
  const fetchReports = useCallback(async (filterParams = {}) => {
    if (!currentCompany) return;
    setLoading(true);
    setError('');
    try {
      const summary = await getReportsSummary(filterParams);
      setData(summary);
    } catch (err) {
      setError(err.message || 'Failed to load reports and analytics.');
    } finally {
      setLoading(false);
    }
  }, [currentCompany]);

  // Synchronize with active company or preset changes
  useEffect(() => {
    let ignore = false;
    if (!currentCompany) return;

    if (!isCustom) {
      getReportsSummary({ preset })
        .then((summary) => {
          if (!ignore) {
            setData(summary);
            setError('');
          }
        })
        .catch((err) => {
          if (!ignore) {
            setError(err.message || 'Failed to load reports and analytics.');
          }
        })
        .finally(() => {
          if (!ignore) {
            setLoading(false);
          }
        });
    }

    return () => {
      ignore = true;
    };
  }, [currentCompany, preset, isCustom]);

  // Handle preset selection
  const handleSelectPreset = (p) => {
    setIsCustom(false);
    setPreset(p);
  };

  // Handle custom date filter apply
  const handleApplyCustomDate = (e) => {
    e.preventDefault();
    if (!customStart || !customEnd) {
      setError('Please provide both start date and end date.');
      return;
    }
    if (customStart > customEnd) {
      setError('Start date cannot be after end date.');
      return;
    }
    fetchReports({ start_date: customStart, end_date: customEnd });
  };

  // Handle PDF Export
  const handleExportPdf = async () => {
    setPdfLoading(true);
    setError('');
    try {
      await downloadFinancialReportPdf();
    } catch (err) {
      setError(err.message || 'Failed to export financial report PDF.');
    } finally {
      setPdfLoading(false);
    }
  };

  // Render SVG Chart for Monthly Comparison (Zero External Dependencies)
  const renderMonthlyChart = (months = []) => {
    if (!months || months.length === 0) {
      return (
        <div className="empty-state-box" style={{ padding: '32px' }}>
          <p>No historical monthly data recorded.</p>
        </div>
      );
    }

    // Determine max value for vertical scaling
    let maxVal = 0;
    months.forEach((m) => {
      const inv = parseFloat(m.invoiced) || 0;
      const col = parseFloat(m.collected) || 0;
      if (inv > maxVal) maxVal = inv;
      if (col > maxVal) maxVal = col;
    });

    if (maxVal === 0) maxVal = 1000; // fallback ceiling

    const chartHeight = 160;

    return (
      <div className="svg-chart-container">
        <div className="chart-bars-wrap">
          {months.map((m, idx) => {
            const invVal = parseFloat(m.invoiced) || 0;
            const colVal = parseFloat(m.collected) || 0;
            const invHeight = Math.max((invVal / maxVal) * chartHeight, 4);
            const colHeight = Math.max((colVal / maxVal) * chartHeight, 4);

            return (
              <div key={idx} className="chart-month-column">
                <div className="bars-pair" style={{ height: `${chartHeight}px` }}>
                  {/* Invoiced Bar */}
                  <div
                    className="chart-bar bar-invoiced"
                    style={{ height: `${invHeight}px` }}
                    title={`Invoiced: ${formatCurrency(invVal)}`}
                  />
                  {/* Collected Bar */}
                  <div
                    className="chart-bar bar-collected"
                    style={{ height: `${colHeight}px` }}
                    title={`Collected: ${formatCurrency(colVal)}`}
                  />
                </div>
                <span className="chart-month-label">{m.month.split(' ')[0]}</span>
              </div>
            );
          })}
        </div>

        {/* Legend */}
        <div className="chart-legend">
          <div className="legend-item">
            <span className="legend-indicator indicator-invoiced" />
            <span>Invoiced Volume</span>
          </div>
          <div className="legend-item">
            <span className="legend-indicator indicator-collected" />
            <span>Collected Cash</span>
          </div>
        </div>
      </div>
    );
  };

  const metrics = data?.metrics || {
    total_invoiced: '0.00',
    total_collected: '0.00',
    total_outstanding: '0.00',
    overdue_amount: '0.00',
    collection_rate: 0.0,
  };

  const invoiceCounts = data?.invoice_counts || {};
  const monthlyTrend = data?.monthly_trend || [];
  const topCustomers = data?.top_customers || [];
  const paymentMethods = data?.payment_methods || [];

  return (
    <div className="reports-container">
      {/* Top Header Card */}
      <section className="card">
        <div className="card-header-flex">
          <div>
            <h2 className="card-title">Financial Reports & Analytics</h2>
            <p className="card-subtitle">
              Comprehensive revenue tracking, receivables aging, and financial audit statements.
            </p>
          </div>

          <button
            type="button"
            className="btn-secondary"
            onClick={handleExportPdf}
            disabled={pdfLoading || loading}
          >
            {pdfLoading ? 'Generating PDF...' : '⬇ Export PDF Report'}
          </button>
        </div>

        {/* Global Error Banner */}
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

        {/* Date Filter Bar */}
        <div className="reports-filter-bar" style={{ marginTop: '20px' }}>
          <div className="preset-pills-group">
            <button
              type="button"
              className={`filter-pill ${preset === '30d' && !isCustom ? 'active' : ''}`}
              onClick={() => handleSelectPreset('30d')}
            >
              Last 30 Days
            </button>
            <button
              type="button"
              className={`filter-pill ${preset === 'this_month' && !isCustom ? 'active' : ''}`}
              onClick={() => handleSelectPreset('this_month')}
            >
              This Month
            </button>
            <button
              type="button"
              className={`filter-pill ${preset === '6m' && !isCustom ? 'active' : ''}`}
              onClick={() => handleSelectPreset('6m')}
            >
              Last 6 Months
            </button>
            <button
              type="button"
              className={`filter-pill ${preset === 'year' && !isCustom ? 'active' : ''}`}
              onClick={() => handleSelectPreset('year')}
            >
              This Year
            </button>
            <button
              type="button"
              className={`filter-pill ${preset === 'all' && !isCustom ? 'active' : ''}`}
              onClick={() => handleSelectPreset('all')}
            >
              All Time
            </button>
            <button
              type="button"
              className={`filter-pill ${isCustom ? 'active' : ''}`}
              onClick={() => setIsCustom(true)}
            >
              Custom Range
            </button>
          </div>

          {/* Custom Date Form */}
          {isCustom && (
            <form onSubmit={handleApplyCustomDate} className="custom-date-form">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="custom-date-input"
                required
              />
              <span className="date-separator">to</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="custom-date-input"
                required
              />
              <button type="submit" className="btn-primary btn-small">
                Apply
              </button>
            </form>
          )}
        </div>
      </section>

      {/* Four Summary Metric Cards */}
      <section className="reports-stats-grid">
        <div className="stat-card">
          <span className="stat-card-label">Revenue Collected</span>
          <span className="stat-card-value" style={{ color: '#4ade80' }}>
            {formatCurrency(metrics.total_collected)}
          </span>
          <span className="stat-card-subtext">Actual payments received</span>
        </div>

        <div className="stat-card">
          <span className="stat-card-label">Revenue Invoiced</span>
          <span className="stat-card-value">
            {formatCurrency(metrics.total_invoiced)}
          </span>
          <span className="stat-card-subtext">Gross billable volume (non-cancelled)</span>
        </div>

        <div className="stat-card">
          <span className="stat-card-label">Outstanding Balance</span>
          <span className="stat-card-value">
            {formatCurrency(metrics.total_outstanding)}
          </span>
          <span className="stat-card-subtext">Current active unpaid receivables</span>
        </div>

        <div className="stat-card">
          <span className="stat-card-label">Overdue Balance</span>
          <span className="stat-card-value" style={{ color: '#f87171' }}>
            {formatCurrency(metrics.overdue_amount)}
          </span>
          <span className="stat-card-subtext">Receivables past due date</span>
        </div>
      </section>

      {/* Main Analytics Grid: 2 Columns */}
      <div className="reports-main-grid">
        {/* Monthly Trend Chart (Left 60%) */}
        <section className="card chart-card">
          <div className="card-header-flex" style={{ marginBottom: '16px' }}>
            <div>
              <h3 className="card-title" style={{ fontSize: '15px' }}>Monthly Revenue Overview</h3>
              <p className="card-subtitle">
                Invoiced volume compared against verified collected cash over past 6 months.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="empty-state-box" style={{ padding: '32px' }}>
              <p>Loading monthly trend...</p>
            </div>
          ) : (
            renderMonthlyChart(monthlyTrend)
          )}
        </section>

        {/* Invoice Status & Collection Efficiency (Right 40%) */}
        <section className="card breakdown-card">
          <div className="card-header-flex" style={{ marginBottom: '16px' }}>
            <div>
              <h3 className="card-title" style={{ fontSize: '15px' }}>Invoice Status Breakdown</h3>
              <p className="card-subtitle">
                Distribution across all lifecycle statuses.
              </p>
            </div>
          </div>

          {loading ? (
            <div className="empty-state-box" style={{ padding: '24px' }}>
              <p>Loading breakdown...</p>
            </div>
          ) : (
            <div className="status-breakdown-list">
              {['PAID', 'SENT', 'OVERDUE', 'DRAFT', 'CANCELLED'].map((st) => {
                const item = invoiceCounts[st] || { label: st, count: 0, total_amount: '0.00' };
                return (
                  <div key={st} className="status-breakdown-row">
                    <div className="status-label-group">
                      <span className={`status-badge status-${st.toLowerCase()}`}>
                        {item.label || st}
                      </span>
                      <span className="status-count-tag">{item.count} invoices</span>
                    </div>
                    <span className="status-amount-tag">
                      {formatCurrency(item.total_amount)}
                    </span>
                  </div>
                );
              })}

              {/* Collection Efficiency Rate */}
              <div className="efficiency-box">
                <div className="efficiency-header">
                  <span className="efficiency-label">Collection Efficiency</span>
                  <span className="efficiency-rate">{metrics.collection_rate}%</span>
                </div>
                <div className="efficiency-bar-track">
                  <div
                    className="efficiency-bar-fill"
                    style={{ width: `${Math.min(metrics.collection_rate, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Lower Analytics Grid: 2 Columns */}
      <div className="reports-lower-grid">
        {/* Top 5 Customers Table */}
        <section className="card">
          <div className="card-header-flex" style={{ marginBottom: '16px' }}>
            <div>
              <h3 className="card-title" style={{ fontSize: '15px' }}>Top Customers</h3>
              <p className="card-subtitle">Ranked by gross invoiced volume.</p>
            </div>
          </div>

          {loading ? (
            <div className="empty-state-box" style={{ padding: '24px' }}>
              <p>Loading customers...</p>
            </div>
          ) : topCustomers.length === 0 ? (
            <div className="empty-state-box" style={{ padding: '24px' }}>
              <p>No customer invoices recorded yet.</p>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="customers-table">
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Invoiced</th>
                    <th>Collected</th>
                    <th>Outstanding</th>
                  </tr>
                </thead>
                <tbody>
                  {topCustomers.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <span className="cell-main-title">{c.name}</span>
                        <span className="cell-subtext" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {c.invoice_count} invoices
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>{formatCurrency(c.total_invoiced)}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: '#4ade80' }}>
                        {formatCurrency(c.total_collected)}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', color: '#fafafa' }}>
                        {formatCurrency(c.outstanding)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Payment Methods Distribution */}
        <section className="card">
          <div className="card-header-flex" style={{ marginBottom: '16px' }}>
            <div>
              <h3 className="card-title" style={{ fontSize: '15px' }}>Payment Methods Distribution</h3>
              <p className="card-subtitle">Breakdown of settled payment channels.</p>
            </div>
          </div>

          {loading ? (
            <div className="empty-state-box" style={{ padding: '24px' }}>
              <p>Loading payment methods...</p>
            </div>
          ) : paymentMethods.length === 0 ? (
            <div className="empty-state-box" style={{ padding: '24px' }}>
              <p>No transactions recorded yet.</p>
            </div>
          ) : (
            <div className="methods-distribution-list">
              {paymentMethods.map((m) => (
                <div key={m.method} className="method-dist-item">
                  <div className="method-dist-header">
                    <span className={`method-badge method-${m.method.toLowerCase()}`}>
                      <span className="method-badge-dot" />
                      {m.display}
                    </span>
                    <div className="method-amount-group">
                      <span className="method-count-tag">{m.count} payments</span>
                      <span className="method-amount-tag">{formatCurrency(m.amount)}</span>
                      <span className="method-pct-tag">{m.percentage}%</span>
                    </div>
                  </div>
                  <div className="method-progress-track">
                    <div
                      className={`method-progress-fill method-fill-${m.method.toLowerCase()}`}
                      style={{ width: `${m.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default Reports;
