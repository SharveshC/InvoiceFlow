/**
 * API utility for communicating with Django REST Framework.
 * Uses native fetch and automatically handles Django CSRF tokens and session cookies.
 */

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + '=') {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

let authFailureHandler = null;
let isHandlingAuthFailure = false;

export function setOnAuthFailure(handler) {
  authFailureHandler = handler;
}

export async function apiRequest(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : endpoint;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const csrftoken = getCookie('csrftoken');
  if (csrftoken && !['GET', 'HEAD', 'OPTIONS'].includes(options.method || 'GET')) {
    headers['X-CSRFToken'] = csrftoken;
  }

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Ensure Django session cookies are sent
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = data?.error || data?.detail || `API request failed with status ${response.status}`;

    // Handle session expiry and unauthenticated responses
    const isUnauthenticated =
      response.status === 401 ||
      (response.status === 403 && data?.detail === 'Authentication credentials were not provided.');

    const isAuthEndpoint =
      endpoint.includes('/api/auth/login/') ||
      endpoint.includes('/api/auth/user/') ||
      endpoint.includes('/api/auth/csrf/');

    if (isUnauthenticated && !isAuthEndpoint && authFailureHandler && !isHandlingAuthFailure) {
      isHandlingAuthFailure = true;
      try {
        authFailureHandler();
      } finally {
        setTimeout(() => {
          isHandlingAuthFailure = false;
        }, 1000);
      }
    }

    throw new Error(errorMsg);
  }

  return data;
}

export async function checkApiHealth() {
  return apiRequest('/api/health/');
}

export async function getCsrfToken() {
  return apiRequest('/api/auth/csrf/');
}

export async function getCurrentUser() {
  return apiRequest('/api/auth/user/');
}

export async function loginUser(email, password) {
  return apiRequest('/api/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function signupUser(fullName, email, password, confirmPassword) {
  return apiRequest('/api/auth/signup/', {
    method: 'POST',
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
      confirm_password: confirmPassword,
    }),
  });
}

export async function logoutUser() {
  return apiRequest('/api/auth/logout/', {
    method: 'POST',
  });
}

export async function createCompany(companyData) {
  return apiRequest('/api/companies/', {
    method: 'POST',
    body: JSON.stringify(companyData),
  });
}

export async function switchCompany(companyId) {
  return apiRequest(`/api/companies/${companyId}/switch/`, {
    method: 'POST',
  });
}


export async function getCustomers(search = '') {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return apiRequest(`/api/customers/${query}`);
}

export async function createCustomer(customerData) {
  return apiRequest('/api/customers/', {
    method: 'POST',
    body: JSON.stringify(customerData),
  });
}

export async function updateCustomer(customerId, customerData) {
  return apiRequest(`/api/customers/${customerId}/`, {
    method: 'PUT',
    body: JSON.stringify(customerData),
  });
}

export async function deleteCustomer(customerId) {
  return apiRequest(`/api/customers/${customerId}/`, {
    method: 'DELETE',
  });
}

export async function getProducts(search = '') {
  const query = search ? `?search=${encodeURIComponent(search)}` : '';
  return apiRequest(`/api/products/${query}`);
}

export async function createProduct(productData) {
  return apiRequest('/api/products/', {
    method: 'POST',
    body: JSON.stringify(productData),
  });
}

export async function updateProduct(productId, productData) {
  return apiRequest(`/api/products/${productId}/`, {
    method: 'PUT',
    body: JSON.stringify(productData),
  });
}

export async function deleteProduct(productId) {
  return apiRequest(`/api/products/${productId}/`, {
    method: 'DELETE',
  });
}

export async function getInvoices(search = '', status = '') {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (status && status !== 'ALL') params.append('status', status);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/api/invoices/${query}`);
}

export async function getInvoice(invoiceId) {
  return apiRequest(`/api/invoices/${invoiceId}/`);
}

export async function createInvoice(invoiceData) {
  return apiRequest('/api/invoices/', {
    method: 'POST',
    body: JSON.stringify(invoiceData),
  });
}

export async function updateInvoice(invoiceId, invoiceData) {
  return apiRequest(`/api/invoices/${invoiceId}/`, {
    method: 'PUT',
    body: JSON.stringify(invoiceData),
  });
}

export async function cancelInvoice(invoiceId) {
  return apiRequest(`/api/invoices/${invoiceId}/cancel/`, {
    method: 'POST',
  });
}

export async function downloadInvoicePdf(invoiceId, invoiceNumber) {
  const response = await fetch(`/api/invoices/${invoiceId}/pdf/`, {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Failed to download invoice PDF.');
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${invoiceNumber || 'invoice'}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function getPayments(search = '', method = '', invoiceId = '') {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (method && method !== 'ALL') params.append('method', method);
  if (invoiceId) params.append('invoice_id', invoiceId);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiRequest(`/api/payments/${query}`);
}

export async function getPayment(paymentId) {
  return apiRequest(`/api/payments/${paymentId}/`);
}

export async function recordPayment(paymentData) {
  return apiRequest('/api/payments/', {
    method: 'POST',
    body: JSON.stringify(paymentData),
  });
}

export async function getReportsSummary(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.preset) queryParams.append('preset', params.preset);
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.end_date) queryParams.append('end_date', params.end_date);
  const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
  return apiRequest(`/api/reports/summary/${query}`);
}

export async function downloadFinancialReportPdf() {
  const response = await fetch('/api/reports/export/', {
    credentials: 'include',
  });
  if (!response.ok) {
    throw new Error('Failed to download financial report PDF.');
  }
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'invoiceflow_report.pdf';
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
