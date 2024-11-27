<template>
  <div class="input-form">
    <h2>AWS Credentials</h2>
    <div class="form-group">
      <input v-model="awsAccessKeyId" placeholder="Access Key ID" class="form-control" />
    </div>
    <div class="form-group">
      <input v-model="awsSecretAccessKey" placeholder="Secret Access Key" class="form-control" />
    </div>
    <div class="form-group">
      <input v-model="awsRegion" placeholder="Region (e.g. us-west-2)" class="form-control" />
    </div>
    <button @click="validateCredentials" class="btn btn-primary">Validate Credentials</button>
    <p v-if="credentialsValidated" :class="{ 'text-success': credentialsValid, 'text-danger': !credentialsValid }">
      {{ credentialsValid ? 'Credentials are valid' : 'Invalid credentials' }}
    </p>

    <div v-if="credentialsValid" class="transcription-mode-container">
      <ul class="nav nav-tabs">
        <li class="nav-item">
          <a class="nav-link" :class="{ active: transcriptionMode === 'realtime' }" href="#" @click.prevent="transcriptionMode = 'realtime'">Real-time Speech Transcription</a>
        </li>
        <li class="nav-item">
          <a class="nav-link" :class="{ active: transcriptionMode === 's3file' }" href="#" @click.prevent="transcriptionMode = 's3file'">S3 Audio File</a>
        </li>
      </ul>

      <div class="tab-content">
        <div class="tab-pane" :class="{ 'active': transcriptionMode === 'realtime' }">
          <div class="realtime-transcription">
            <AudioRecorder ref="audioRecorder" @audioChunk="handleAudioChunk" @recordingStopped="handleRecordingStopped" />
            <div v-if="isMatching" class="status-text">
              {{ matchStatus }}
            </div>
            <div v-if="transcriptionResult" class="transcription-result">
              <h3>Match Result</h3>
              <pre>{{ transcriptionResult }}</pre>
            </div>
          </div>
        </div>

        <div class="tab-pane" :class="{ 'active': transcriptionMode === 's3file' }">
          <div class="s3file-transcription">
            <div class="form-group">
              <label for="s3AudioFileUrl">S3 Audio File URL</label>
              <input type="text" id="s3AudioFileUrl" v-model="s3AudioFileUrl" placeholder="Enter S3 Audio File URL" class="form-control" />
            </div>
            <div class="form-group">
              <label for="systemPrompt">System Prompt</label>
              <textarea id="systemPrompt" v-model="systemPrompt" placeholder="Enter system prompt" class="form-control"></textarea>
            </div>
            <button @click="submitInputs" class="btn btn-primary">Submit</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="result">
      <h2>Result</h2>
      <div class="result-container">
        <div class="transcript-container">
          <h3>Transcript</h3>
          <pre>{{ result.transcript }}</pre>
        </div>
        <div class="bedrock-result-container">
          <h3>Bedrock Claude Result</h3>
          <pre>{{ result.bedrock_claude_result }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import './InputForm.css'
import AudioRecorder from './AudioRecorder.vue'

const BACKEND_URL = 'http://localhost:8000'
const BACKEND_WS_URL = 'ws://localhost:8000'

export default {
  name: 'InputForm',
  components: {
    AudioRecorder,
  },
  data() {
    return {
      awsAccessKeyId: '',
      awsSecretAccessKey: '',
      awsRegion: 'us-west-2',
      s3AudioFileUrl: '',
      systemPrompt: '',
      result: null,
      credentialsValid: false,
      credentialsValidated: false,
      isMatching: false,
      matchStatus: 'Matching...',
      transcriptionResult: '',
      webSocket: null,
      webSocketConnected: false,
      transcriptionMode: 'realtime', // or 's3file'
      pendingAudioChunks: [],
    }
  },
  methods: {
    async validateCredentials() {
      try {
        const response = await fetch(`${BACKEND_URL}/validate_credentials`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            aws_access_key_id: this.awsAccessKeyId,
            aws_secret_access_key: this.awsSecretAccessKey,
            aws_region: this.awsRegion
          })
        })
        if (response.ok) {
          this.credentialsValid = true
        } else {
          this.credentialsValid = false
        }
      } catch (error) {
        console.error('Error validating credentials:', error)
        this.credentialsValid = false
      } finally {
        this.credentialsValidated = true
      }
    },
    async submitInputs() {
      const response = await fetch(`${BACKEND_URL}/transcribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          s3_audio_url: this.s3AudioFileUrl,
          system_prompt: this.systemPrompt,
          aws_access_key_id: this.awsAccessKeyId,
          aws_secret_access_key: this.awsSecretAccessKey,
          aws_region: this.awsRegion
        })
      })
      if (response.ok) {
        this.result = await response.json()
      } else {
        alert(`Error: ${response.status} - ${response.statusText}`)
      }
    },
    handleAudioChunk(audioChunk) {
      if (!this.isMatching) {
        this.startMatching()
        // Store the chunk until WebSocket is connected
        this.pendingAudioChunks.push(audioChunk)
      } else {
        console.log('Received audio chunk of size', audioChunk.byteLength)
        this.sendAudioChunk(audioChunk)
      }
    },
    handleRecordingStopped() {
      this.stopMatching()
    },
    startMatching() {
      this.isMatching = true
      this.transcriptionResult = ''
      this.webSocketConnected = false
      this.pendingAudioChunks = []

      const webSocketUrl = `${BACKEND_WS_URL}/ws/client-id`
      console.log('Connecting to WebSocket:', webSocketUrl)

      this.webSocket = new WebSocket(webSocketUrl)
      
      this.webSocket.onopen = () => {
        console.log('WebSocket connection opened')
        // First send AWS credentials
        const credentials = {
          aws_access_key_id: this.awsAccessKeyId,
          aws_secret_access_key: this.awsSecretAccessKey,
          aws_region: this.awsRegion
        }
        this.webSocket.send(JSON.stringify(credentials))
        this.webSocketConnected = true

        // Send any pending audio chunks
        while (this.pendingAudioChunks.length > 0) {
          const chunk = this.pendingAudioChunks.shift()
          this.sendAudioChunk(chunk)
        }
      }

      this.webSocket.onmessage = (event) => {
        this.transcriptionResult += event.data
      }

      this.webSocket.onclose = () => {
        this.isMatching = false
        this.webSocketConnected = false
        console.log('WebSocket connection closed')
      }

      this.webSocket.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.isMatching = false
        this.webSocketConnected = false
        this.matchStatus = 'Error occurred during matching'
      }
    },
    sendAudioChunk(audioChunk) {
      if (this.webSocketConnected) {
        console.log('Sending audio chunk of size', audioChunk.byteLength)
        this.webSocket.send(audioChunk)
      } else {
        console.error('WebSocket is not open, cannot send audio chunk')
        // Store the chunk until WebSocket is connected
        this.pendingAudioChunks.push(audioChunk)
      }
    },
    stopMatching() {
      if (this.webSocket) {
        this.webSocket.close()
        this.webSocket = null
        this.webSocketConnected = false
        this.pendingAudioChunks = []
        console.log('WebSocket connection closed')
      }
    }
  },
}
</script>

<style scoped>
.input-form {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

.form-group {
  margin-bottom: 20px;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 3px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  margin-right: 10px;
}

.btn-primary {
  background-color: #007bff;
  color: #fff;
}

.transcription-mode-container {
  border: 1px solid #ccc;
  border-radius: 5px;
  padding: 20px;
  margin-top: 20px;
}

.nav-tabs {
  display: flex;
  list-style: none;
  padding: 0;
  margin-bottom: 20px;
}

.nav-item {
  margin-right: 10px;
}

.nav-link {
  display: block;
  padding: 10px 15px;
  text-decoration: none;
  color: #333;
  background-color: #f0f0f0;
  border-radius: 5px;
}

.nav-link.active {
  background-color: #007bff;
  color: #fff;
}

.tab-content {
  margin-top: 20px;
}

.tab-pane {
  display: none;
}

.tab-pane.active {
  display: block;
}

.status-text {
  margin: 20px 0;
  font-weight: bold;
  color: #007bff;
}

.transcription-result {
  margin-top: 20px;
  border: 1px solid #ccc;
  padding: 10px;
  border-radius: 5px;
}

.result-container {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-top: 20px;
}

.transcript-container,
.bedrock-result-container {
  flex: 1;
  border: 1px solid #ccc;
  padding: 10px;
  border-radius: 5px;
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.text-success {
  color: green;
}

.text-danger {
  color: red;
}
</style>
