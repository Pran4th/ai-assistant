<template>
  <button @click="toggleRecording" :class="['voice-btn', { recording: isRecording }]" :title="error || 'Voice input'">
    <svg v-if="!isRecording" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
      <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"/>
      <path d="M19 10v2a7 7 0 01-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
    <span v-if="isRecording" class="rec-icon"></span>
  </button>
  <div v-if="error" class="voice-error">{{ error }}</div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['transcription'])
const isRecording = ref(false)
const error = ref('')
let recognition = null

const toggleRecording = () => {
  error.value = ''
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

const startRecording = () => {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    error.value = 'Not supported — try Chrome'
    return
  }

  try {
    recognition = new SpeechRecognition()
    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => { isRecording.value = true; error.value = '' }
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      emit('transcription', transcript)
    }
    recognition.onerror = (event) => {
      if (event.error === 'not-allowed') error.value = 'Mic denied — allow in browser settings'
      else if (event.error === 'no-speech') error.value = 'No speech detected'
      else if (event.error === 'network') error.value = 'Network error — check connection'
      else error.value = `Error: ${event.error}`
      isRecording.value = false
    }
    recognition.onend = () => { isRecording.value = false }
    recognition.start()
  } catch (e) {
    error.value = 'Failed to start voice'
    isRecording.value = false
  }
}

const stopRecording = () => {
  if (recognition) { try { recognition.stop() } catch (e) {} }
  isRecording.value = false
}
</script>

<style scoped>
.voice-btn {
  width: 42px; height: 42px;
  background: #f1f3f5;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  transition: all 0.2s;
  flex-shrink: 0;
}
.voice-btn:hover { background: #e9ecef; color: #4f46e5; }
.voice-btn.recording {
  background: #fee2e2;
  color: #e53e3e;
  animation: pulse 1s infinite;
}
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
.rec-icon {
  width: 10px; height: 10px;
  background: #e53e3e;
  border-radius: 50%;
}
.voice-error { font-size: 0.7rem; color: #e53e3e; white-space: nowrap; }
</style>
