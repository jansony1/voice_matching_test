<template>
  <div class="input-form">
    <h2>AWS Credentials</h2>
    <div class="form-group">
      <div class="input-group">
        <input 
          :type="showAccessKeyId ? 'text' : 'password'" 
          v-model="awsAccessKeyId" 
          placeholder="Access Key ID" 
          class="form-control" 
        />
        <div class="input-group-append">
          <button 
            @click="toggleAccessKeyVisibility" 
            class="btn btn-outline-secondary"
          >
            {{ showAccessKeyId ? 'Hide' : 'Show' }}
          </button>
        </div>
      </div>
    </div>
    <div class="form-group">
      <div class="input-group">
        <input 
          :type="showSecretAccessKey ? 'text' : 'password'" 
          v-model="awsSecretAccessKey" 
          placeholder="Secret Access Key" 
          class="form-control" 
        />
        <div class="input-group-append">
          <button 
            @click="toggleSecretKeyVisibility" 
            class="btn btn-outline-secondary"
          >
            {{ showSecretAccessKey ? 'Hide' : 'Show' }}
          </button>
        </div>
      </div>
    </div>
    <div class="form-group">
      <input v-model="awsRegion" placeholder="Region (e.g. us-west-2)" class="form-control" />
    </div>
    <button @click="validateCredentials" class="btn btn-primary">Validate Credentials</button>
    <p v-if="credentialsValidated" :class="{ 'text-success': credentialsValid, 'text-danger': !credentialsValid }">
      {{ credentialsValid ? 'Credentials are valid' : 'Invalid credentials' }}
    </p>

    <div v-if="credentialsValid" class="transcription-mode-container">
      <div class="form-group">
        <label for="systemPrompt">System Prompt</label>
        <textarea id="systemPrompt" v-model="systemPrompt" placeholder="Enter system prompt" class="form-control"></textarea>
      </div>

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
            <AudioRecorder 
              ref="audioRecorder" 
              :awsCredentials="awsCredentials"
              :systemPrompt="systemPrompt"
              @transcriptionUpdate="handleTranscriptionUpdate"
              @recordingStopped="handleRecordingStopped"
              @recordingStarted="handleRecordingStarted"
            />
            <div v-if="status === 'matching'" class="status-text">
              Matching...
            </div>
            <div v-if="status === 'matched'" class="status-text">
              Match Result
            </div>
            <div v-if="transcriptionResult" class="transcription-result">
              <h3>Transcription Result</h3>
              <pre>{{ transcriptionResult }}</pre>
            </div>
            <div v-if="bedrockResult" class="bedrock-result">
              <h3>Bedrock Inference Result</h3>
              <pre>{{ bedrockResult }}</pre>
            </div>
          </div>
        </div>

        <div class="tab-pane" :class="{ 'active': transcriptionMode === 's3file' }">
          <div class="s3file-transcription">
            <div class="form-group">
              <label for="s3AudioFileUrl">S3 Audio File URL</label>
              <input type="text" id="s3AudioFileUrl" v-model="s3AudioFileUrl" placeholder="Enter S3 Audio File URL" class="form-control" />
            </div>
            <button @click="submitS3Transcription" :disabled="s3Status === 'matching'" class="btn btn-primary">
              {{ s3Status === 'matching' ? 'Matching...' : 'Submit' }}
            </button>
            <div v-if="s3Status === 'matched'" class="status-text">
              Match Result
            </div>
            <div v-if="transcriptionResult" class="transcription-result">
              <h3>S3 Transcription Result</h3>
              <pre>{{ transcriptionResult }}</pre>
            </div>
            <div v-if="bedrockResult" class="bedrock-result">
              <h3>S3 Bedrock Inference Result</h3>
              <pre>{{ bedrockResult }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script>
import './InputForm.css'
import AudioRecorder from './AudioRecorder.vue'

const BACKEND_URL = 'http://localhost:8000'

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
      credentialsValid: false,
      credentialsValidated: false,
      transcriptionResult: '',
      bedrockResult: '',
      transcriptionMode: 'realtime',
      status: 'idle',
      s3Status: 'idle',
      error: null,
      showAccessKeyId: false,
      showSecretAccessKey: false
    }
  },
  computed: {
    awsCredentials() {
      return {
        accessKeyId: this.awsAccessKeyId,
        secretAccessKey: this.awsSecretAccessKey,
        region: this.awsRegion
      }
    }
  },
  methods: {
    toggleAccessKeyVisibility() {
      this.showAccessKeyId = !this.showAccessKeyId
    },
    toggleSecretKeyVisibility() {
      this.showSecretAccessKey = !this.showSecretAccessKey
    },
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
    async submitS3Transcription() {
      this.s3Status = 'matching'
      this.transcriptionResult = ''
      this.bedrockResult = ''
      this.error = null

      try {
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
          const result = await response.json()
          this.transcriptionResult = result.transcript
          this.bedrockResult = result.bedrock_claude_result
          this.s3Status = 'matched'
        } else {
          throw new Error(`Error: ${response.status} - ${response.statusText}`)
        }
      } catch (error) {
        console.error('Error submitting S3 transcription:', error)
        this.error = `Error submitting S3 transcription: ${error.message}`
        this.s3Status = 'idle'
      }
    },
    handleTranscriptionUpdate(transcription) {
      this.transcriptionResult = transcription
      this.status = 'matching'
    },
    async handleRecordingStopped(finalTranscription) {
      this.transcriptionResult = finalTranscription
      this.status = 'matched'
      await this.callBedrock(finalTranscription)
    },
    handleRecordingStarted() {
      this.status = 'matching'
      this.transcriptionResult = ''
      this.bedrockResult = ''
    },
    async callBedrock(transcription) {
      try {
        const response = await fetch(`${BACKEND_URL}/bedrock`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            transcript: transcription,
            system_prompt: this.systemPrompt,
            aws_access_key_id: this.awsAccessKeyId,
            aws_secret_access_key: this.awsSecretAccessKey,
            aws_region: this.awsRegion
          })
        })
        if (response.ok) {
          const result = await response.json()
          this.bedrockResult = result.bedrock_result
        } else {
          throw new Error(`Error: ${response.status} - ${response.statusText}`)
        }
      } catch (error) {
        console.error('Error calling Bedrock:', error)
        this.error = `Error calling Bedrock: ${error.message}`
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

.input-group {
  display: flex;
}

.input-group-append {
  margin-left: 10px;
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

.btn-outline-secondary {
  background-color: #f8f9fa;
  border: 1px solid #ccc;
  color: #333;
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

.transcription-result, .bedrock-result {
  margin-top: 20px;
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

.error-message {
  color: red;
  margin-top: 10px;
}
</style>
