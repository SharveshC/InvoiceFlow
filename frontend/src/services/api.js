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

