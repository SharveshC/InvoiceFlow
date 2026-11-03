import { useState, useEffect, useCallback } from 'react';
import {
  getProducts,
  createProduct,
  updateProduct,
  deleteProduct,
} from '../services/api';

function Products({ currentCompany }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form State
  const [showForm, setShowForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState('');
  const [tax, setTax] = useState('');
  const [formLoading, setFormLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  // Fetch products helper
  const fetchProducts = useCallback(async (searchQuery = '') => {
    if (!currentCompany) return;
    setLoading(true);
    try {
      const data = await getProducts(searchQuery);
      setProducts(data);
    } catch (err) {
      setError(err.message || 'Failed to load products.');
    } finally {
      setLoading(false);
    }
  }, [currentCompany]);

  // Load products whenever currentCompany or search changes
  useEffect(() => {
    let ignore = false;
    if (!currentCompany) return;

    getProducts(search)
      .then((data) => {
        if (!ignore) {
          setProducts(data);
        }
      })
      .catch((err) => {
        if (!ignore) {
          setError(err.message || 'Failed to load products.');
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
  }, [currentCompany, search]);

  const handleOpenCreateForm = () => {
    setEditingProduct(null);
    setName('');
    setDescription('');
    setPrice('');
    setTax('');
    setError('');
    setShowForm(true);
  };

  const handleOpenEditForm = (prod) => {
    setEditingProduct(prod);
    setName(prod.name || '');
    setDescription(prod.description || '');
    setPrice(prod.price !== undefined && prod.price !== null ? String(prod.price) : '');
    setTax(prod.tax !== undefined && prod.tax !== null ? String(prod.tax) : '0');
    setError('');
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingProduct(null);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!name.trim() || price.trim() === '') {
      setError('Product name and price are required.');
      return;
    }

    const numPrice = parseFloat(price);
    const numTax = tax.trim() === '' ? 0 : parseFloat(tax);

    if (isNaN(numPrice) || numPrice < 0 || isNaN(numTax) || numTax < 0) {
      setError('Please enter valid non-negative numbers for price and tax.');
      return;
    }

    setFormLoading(true);
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || null,
        price: numPrice.toFixed(2),
        tax: numTax.toFixed(2),
      };

      if (editingProduct) {
        await updateProduct(editingProduct.id, payload);
        setSuccess('Product updated successfully!');
      } else {
        await createProduct(payload);
        setSuccess('Product created successfully!');
      }

      handleCloseForm();
      fetchProducts(search);
    } catch (err) {
      setError(err.message || 'Operation failed.');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDeleteProduct = async (prod) => {
    const confirmed = window.confirm(`Are you sure you want to delete product "${prod.name}"?`);
    if (!confirmed) return;

    setError('');
    setSuccess('');
    setDeletingId(prod.id);

    try {
      await deleteProduct(prod.id);
      setSuccess(`Product "${prod.name}" deleted successfully.`);
      fetchProducts(search);
    } catch (err) {
      setError(err.message || 'Failed to delete product.');
    } finally {
      setDeletingId(null);
    }
  };

  if (!currentCompany) {
    return (
      <div className="card empty-state-box">
        <h4>No Active Company Selected</h4>
        <p>Please create or select an active company on the dashboard first.</p>
      </div>
    );
  }

  return (
    <div className="products-module">
      {/* Module Header */}
      <div className="module-header-flex">
        <div>
          <h2 className="module-title">Products & Services</h2>
          <p className="module-subtitle">
            Catalog items, pricing, and tax rates for {currentCompany.name}
          </p>
        </div>

        <button
          type="button"
          className="btn-primary"
          onClick={handleOpenCreateForm}
        >
          + Add Product
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
          placeholder="Search products by name or description..."
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

      {/* Product Create / Edit Form Card */}
      {showForm && (
        <section className="card">
          <div className="card-header-flex">
            <div>
              <h3 className="card-title">
                {editingProduct ? 'Edit Product' : 'Add New Product'}
              </h3>
              <p className="card-subtitle">
                {editingProduct
                  ? 'Update product pricing, tax rate, or description.'
                  : 'Add a new catalog item or service for client invoicing.'}
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

          <form onSubmit={handleFormSubmit} className="product-form">
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="prod-name">Product / Service Name *</label>
                <input
                  id="prod-name"
                  type="text"
                  placeholder="Web Development Consulting"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="prod-price">Unit Price (₹) *</label>
                <input
                  id="prod-price"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="1500.00"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  disabled={formLoading}
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="prod-tax">Tax Rate (%) (Optional)</label>
                <input
                  id="prod-tax"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="18.00"
                  value={tax}
                  onChange={(e) => setTax(e.target.value)}
                  disabled={formLoading}
                />
              </div>

              <div className="form-group full-width">
                <label htmlFor="prod-desc">Description (Optional)</label>
                <textarea
                  id="prod-desc"
                  rows="3"
                  placeholder="Detailed description of the service or item..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={formLoading}
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
                  : editingProduct
                  ? 'Save Changes'
                  : 'Create Product'}
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

      {/* Products Data Table / List */}
      {loading ? (
        <div className="loading-spinner">Loading products...</div>
      ) : products.length === 0 ? (
        <div className="card empty-state-box">
          {search ? (
            <>
              <h4>No products match your search</h4>
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
              <h4>No products added yet</h4>
              <p>Add your first product or service to start building invoices.</p>
              <button
                type="button"
                className="btn-primary btn-small"
                onClick={handleOpenCreateForm}
              >
                + Add Product
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="table-responsive">
          <table className="products-table">
            <thead>
              <tr>
                <th>Product / Service</th>
                <th>Description</th>
                <th>Unit Price</th>
                <th>Tax Rate</th>
                <th>Added</th>
                <th className="th-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((prod) => (
                <tr key={prod.id}>
                  <td>
                    <span className="customer-name-cell">{prod.name}</span>
                  </td>
                  <td className="address-cell" title={prod.description || '—'}>
                    {prod.description || <span className="text-muted-dash">—</span>}
                  </td>
                  <td>
                    <span className="price-tag">
                      ₹{parseFloat(prod.price).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                  </td>
                  <td>
                    {parseFloat(prod.tax) > 0 ? (
                      <span className="tax-tag">{parseFloat(prod.tax)}%</span>
                    ) : (
                      <span className="text-muted-dash">0%</span>
                    )}
                  </td>
                  <td>
                    <span className="product-date">
                      {prod.created_at ? new Date(prod.created_at).toLocaleDateString() : '—'}
                    </span>
                  </td>
                  <td className="actions-cell">
                    <button
                      type="button"
                      className="btn-secondary btn-small"
                      onClick={() => handleOpenEditForm(prod)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn-danger-outline"
                      onClick={() => handleDeleteProduct(prod)}
                      disabled={deletingId === prod.id}
                    >
                      {deletingId === prod.id ? '...' : 'Delete'}
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

export default Products;

