import { reactive } from 'vue'

const state = reactive({
  token: localStorage.getItem('access_token') || null,
  user: JSON.parse(localStorage.getItem('user') || 'null'),
})

export function useAuthStore() {
  return {
    get isAuthenticated() {
      return !!state.token
    },
    get token() {
      return state.token
    },
    get user() {
      return state.user
    },
    setToken(token) {
      state.token = token
      localStorage.setItem('access_token', token)
    },
    setUser(user) {
      state.user = user
      localStorage.setItem('user', JSON.stringify(user))
    },
    logout() {
      state.token = null
      state.user = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
    },
  }
}
