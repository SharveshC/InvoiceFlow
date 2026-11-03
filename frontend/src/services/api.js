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
