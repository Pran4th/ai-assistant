<template>
  <div id="app">
    <div v-if="!isAuthenticated" class="auth-screen">
      <div class="auth-card">
        <div class="auth-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="#4f46e5" stroke-width="2" width="48" height="48">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        </div>
        <h1>AI Personal Assistant</h1>
        <p>Manage your Google Calendar, Tasks, Gmail, and Contacts with natural language</p>
        <AuthButton />
      </div>
    </div>
    <div v-else>
      <ChatInterface />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ChatInterface from './components/ChatInterface.vue'
import AuthButton from './components/AuthButton.vue'
import { useAuthStore } from './stores/auth'

const authStore = useAuthStore()
const isAuthenticated = ref(false)

onMounted(() => {
  isAuthenticated.value = authStore.isAuthenticated
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Roboto, sans-serif;
  background: #f8f9fa;
  color: #1a1a2e;
  -webkit-font-smoothing: antialiased;
}
.auth-screen {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.auth-card {
  background: white;
  border-radius: 16px;
  padding: 3rem;
  text-align: center;
  max-width: 420px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.auth-logo { margin-bottom: 1.5rem; }
.auth-card h1 { font-size: 1.5rem; margin-bottom: 0.75rem; color: #1a1a2e; }
.auth-card p { font-size: 0.9rem; color: #666; margin-bottom: 2rem; line-height: 1.5; }
</style>
