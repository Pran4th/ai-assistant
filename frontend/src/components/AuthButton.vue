<template>
  <div v-if="isAuthenticated" class="user-menu">
    <img :src="user.picture" :alt="user.name" class="avatar" v-if="user.picture" />
    <span class="user-name">{{ user.name }}</span>
    <button @click="logout" class="logout-btn">Sign out</button>
  </div>
  <button v-else @click="login" class="google-btn">Sign in with Google</button>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isAuthenticated = ref(false)
const user = ref({})

onMounted(() => {
  isAuthenticated.value = authStore.isAuthenticated
  user.value = authStore.user || {}

  const params = new URLSearchParams(window.location.search)
  const token = params.get('token')
  if (token) {
    authStore.setToken(token)
    if (params.get('user')) {
      authStore.setUser(JSON.parse(decodeURIComponent(params.get('user'))))
    }
    window.history.replaceState({}, document.title, window.location.pathname)
    isAuthenticated.value = true
    user.value = authStore.user || {}
  }
})

const login = async () => {
  try {
    const response = await fetch('/auth/google')
    const data = await response.json()
    window.location.href = data.auth_url
  } catch (err) {
    console.error('Login failed:', err)
  }
}

const logout = () => {
  authStore.logout()
  isAuthenticated.value = false
  user.value = {}
  window.location.reload()
}
</script>

<style scoped>
.user-menu { display: flex; align-items: center; gap: 0.5rem; }
.avatar { width: 28px; height: 28px; border-radius: 50%; }
.user-name { font-size: 0.85rem; color: #333; display: none; }
@media (min-width: 640px) { .user-name { display: inline; } }
.logout-btn {
  padding: 0.3rem 0.7rem;
  background: transparent;
  border: 1px solid #d0d0ff;
  border-radius: 6px;
  color: #4f46e5;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.2s;
}
.logout-btn:hover { background: #f0f0ff; }
.google-btn {
  padding: 0.5rem 1rem;
  background: #fff;
  color: #4f46e5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s;
}
.google-btn:hover { background: #f0f0ff; }
</style>
