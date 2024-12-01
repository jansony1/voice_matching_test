<template>
  <div class="speech-transcription">
    <h2>Real-time Speech Transcription</h2>
    <div class="recorder-container">
      <AudioRecorder ref="audioRecorder" @audioBlob="handleAudioBlob" />
    </div>
    <div v-if="transcriptionResult">
      <div class="result-container">
        <div class="transcript-container">
          <h3>Transcript</h3>
          <pre>{{ transcriptionResult }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import AudioRecorder from './AudioRecorder.vue'

export default {
  name: 'SpeechTranscription',
  components: {
    AudioRecorder,
  },
  data() {
    return {
      transcriptionResult: '',
      webSocket: null,
    }
  },
  methods: {
    handleAudioBlob(audioBlob) {
      this.startTranscription(audioBlob)
    },
    startTranscription(audioBlob) {
      this.transcriptionResult = ''

      this.webSocket = new WebSocket('ws://localhost:8006/ws/client-id')
      this.webSocket.onopen = () => {
        this.webSocket.send(audioBlob)
      }
      this.webSocket.onmessage = (event) => {
        this.transcriptionResult += event.data
      }
      this.webSocket.onclose = () => {
        // Handle WebSocket closure
      }
      this.webSocket.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    },
  },
}
</script>

<style scoped>
.speech-transcription {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

.recorder-container {
  margin-bottom: 20px;
}

.result-container {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.transcript-container {
  flex: 1;
  border: 1px solid #ccc;
  padding: 10px;
  border-radius: 5px;
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
