const API_BASE = import.meta.env.VITE_API_URL || ''

async function request(endpoint, options = {}) {
  const token = localStorage.getItem('access_token')
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || 'Request failed')
  }

  return response.json()
}

export function getWsUrl() {
  const apiUrl = import.meta.env.VITE_API_URL || ''
  if (apiUrl) {
    const url = new URL(apiUrl)
    return `${url.protocol === 'https:' ? 'wss:' : 'ws:'}//${url.host}`
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}`
}

export const api = {
  chat: (message) => request('/api/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  voice: (audioData) => request('/api/voice', { method: 'POST', body: JSON.stringify({ audio_data: audioData }) }),
  voiceText: (text) => request('/api/voice', { method: 'POST', body: JSON.stringify({ text }) }),
  health: () => request('/health'),
  getAuthUrl: () => request('/auth/google'),
}
