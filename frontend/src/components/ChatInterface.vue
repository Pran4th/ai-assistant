<template>
  <div class="chat-container">
    <div class="chat-header">
      <div class="header-left">
        <div class="bot-avatar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        </div>
        <div>
          <h2>AI Assistant</h2>
          <span class="status-text" :class="{ online: isConnected }">
            {{ isConnected ? 'Online' : 'Reconnecting...' }}
          </span>
        </div>
      </div>
      <div class="header-right">
        <AuthButton />
      </div>
    </div>

    <div class="messages" ref="messagesContainer">
      <div v-if="messages.length === 0 && !isProcessing" class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="#999" stroke-width="1.5">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <h3>How can I help you?</h3>
        <p>Try asking about your calendar, tasks, emails, or contacts</p>
        <div class="quick-actions">
          <button @click="sendMessage('Show my events today')">Show my events</button>
          <button @click="sendMessage('What\'s in my inbox?')">Check inbox</button>
          <button @click="sendMessage('Add a task to buy groceries')">Add a task</button>
          <button @click="sendMessage('List my contacts')">My contacts</button>
        </div>
      </div>

      <div v-for="msg in messages" :key="msg.id" :class="['message', msg.type]">
        <div class="bubble">
          <div class="msg-content">{{ msg.content }}</div>
          <div v-if="msg.suggestions && msg.suggestions.length" class="suggestions">
            <button v-for="s in msg.suggestions" :key="s" @click="sendMessage(s)">{{ s }}</button>
          </div>
          <div v-if="msg.requiresConfirmation" class="confirmation">
            <button @click="confirmAction(true)" class="btn-confirm">Yes</button>
            <button @click="confirmAction(false)" class="btn-cancel">Cancel</button>
          </div>
          <div class="msg-time">{{ msg.time }}</div>
        </div>
      </div>

      <div v-if="isProcessing" class="message assistant">
        <div class="bubble typing">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      </div>
    </div>

    <div class="input-area">
      <VoiceInput @transcription="handleVoiceInput" />
      <div class="input-wrapper">
        <input
          v-model="inputMessage"
          @keyup.enter="sendMessage()"
          placeholder="Type your message..."
          :disabled="isProcessing"
        />
        <button @click="sendMessage()" :disabled="isProcessing || !inputMessage.trim()" class="send-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import VoiceInput from './VoiceInput.vue'
import AuthButton from './AuthButton.vue'
import { getWsUrl } from '../services/api.js'

const messages = ref([])
const inputMessage = ref('')
const isProcessing = ref(false)
const isConnected = ref(false)
const messagesContainer = ref(null)
let ws = null

onMounted(() => {
  const token = localStorage.getItem('access_token')
  if (token) connectWebSocket(token)
})

onUnmounted(() => {
  if (ws) ws.close()
})

const connectWebSocket = (token) => {
  ws = new WebSocket(`${getWsUrl()}/ws/chat?token=${token}`)

  ws.onopen = () => { isConnected.value = true }
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleResponse(data)
  }
  ws.onclose = () => {
    isConnected.value = false
    setTimeout(() => {
      const t = localStorage.getItem('access_token')
      if (t) connectWebSocket(t)
    }, 3000)
  }
}

const sendMessage = (text = null) => {
  const message = text || inputMessage.value
  if (!message.trim()) return

  messages.value.push({
    id: Date.now(),
    type: 'user',
    content: message,
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  })
  inputMessage.value = ''
  isProcessing.value = true
  scrollToBottom()

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ message }))
  }
}

const handleResponse = (data) => {
  isProcessing.value = false
  if (data.type === 'response') {
    messages.value.push({
      id: Date.now(),
      type: 'assistant',
      content: data.content,
      action: data.action,
      data: data.data,
      suggestions: data.suggestions || [],
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    })
  } else if (data.type === 'clarification') {
    messages.value.push({
      id: Date.now(),
      type: 'assistant',
      content: data.question,
      requiresConfirmation: true,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    })
  } else if (data.type === 'error') {
    messages.value.push({
      id: Date.now(),
      type: 'error',
      content: data.message,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    })
  }
  scrollToBottom()
}

const handleVoiceInput = (transcription) => {
  inputMessage.value = transcription
  sendMessage()
}

const confirmAction = (confirmed) => {
  const last = messages.value[messages.value.length - 1]
  if (last && last.requiresConfirmation) {
    messages.value.pop()
    sendMessage(confirmed ? 'yes' : 'no')
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 860px;
  margin: 0 auto;
  background: #f8f9fa;
}

.chat-header {
  padding: 0.75rem 1.25rem;
  background: white;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 0.75rem; }
.bot-avatar {
  width: 40px; height: 40px;
  background: #4f46e5;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: white;
}
.bot-avatar svg { width: 22px; height: 22px; }
.chat-header h2 { font-size: 1rem; font-weight: 600; color: #1a1a2e; margin: 0; }
.status-text { font-size: 0.75rem; color: #adb5bd; }
.status-text.online { color: #2ecc71; }

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 2rem;
}
.empty-icon svg { width: 48px; height: 48px; margin-bottom: 1rem; }
.empty-state h3 { font-size: 1.25rem; color: #1a1a2e; margin-bottom: 0.5rem; }
.empty-state p { color: #999; font-size: 0.9rem; margin-bottom: 1.5rem; }
.quick-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }
.quick-actions button {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 20px;
  color: #4f46e5;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}
.quick-actions button:hover { background: #f0f0ff; border-color: #4f46e5; }

.message { display: flex; margin-bottom: 0.25rem; }
.message.user { justify-content: flex-end; }
.message.assistant, .message.error { justify-content: flex-start; }

.bubble {
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 16px;
  line-height: 1.5;
  font-size: 0.9rem;
  position: relative;
}
.message.user .bubble {
  background: #4f46e5;
  color: white;
  border-bottom-right-radius: 4px;
}
.message.assistant .bubble {
  background: white;
  color: #1a1a2e;
  border: 1px solid #e9ecef;
  border-bottom-left-radius: 4px;
}
.message.error .bubble {
  background: #fff5f5;
  color: #e53e3e;
  border: 1px solid #fed7d7;
  border-bottom-left-radius: 4px;
}

.msg-content { white-space: pre-wrap; word-break: break-word; }
.msg-time { font-size: 0.7rem; color: #adb5bd; margin-top: 0.35rem; text-align: right; }
.message.user .msg-time { color: rgba(255,255,255,0.7); }

.suggestions { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.6rem; }
.suggestions button {
  padding: 0.35rem 0.75rem;
  background: #f0f0ff;
  border: 1px solid #d0d0ff;
  border-radius: 14px;
  color: #4f46e5;
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s;
}
.suggestions button:hover { background: #e0e0ff; }

.confirmation { display: flex; gap: 0.5rem; margin-top: 0.6rem; }
.btn-confirm, .btn-cancel {
  padding: 0.4rem 1rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
}
.btn-confirm { background: #2ecc71; color: white; }
.btn-cancel { background: #e74c3c; color: white; }

.typing { display: flex; gap: 4px; align-items: center; padding: 0.75rem 1rem; }
.dot {
  width: 8px; height: 8px;
  background: #adb5bd;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}
.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
.dot:nth-child(3) { animation-delay: 0s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.input-area {
  padding: 1rem 1.25rem;
  background: white;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-shrink: 0;
}
.input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  background: #f1f3f5;
  border-radius: 24px;
  padding: 0.35rem 0.35rem 0.35rem 1rem;
}
.input-wrapper input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0.5rem 0;
  outline: none;
  font-size: 0.9rem;
  color: #1a1a2e;
}
.input-wrapper input::placeholder { color: #adb5bd; }
.send-btn {
  width: 38px; height: 38px;
  background: #4f46e5;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.send-btn:hover { background: #4338ca; }
.send-btn:disabled { background: #d0d0ff; cursor: not-allowed; }
.send-btn svg { width: 16px; height: 16px; color: white; }
</style>
