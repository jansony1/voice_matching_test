<template>
  <div class="input-form">
    <button @click="fetchEC2Role" class="btn btn-primary" :disabled="isFetchingRole">
      {{ isFetchingRole ? 'Fetching EC2 Role...' : 'Get EC2 Role and Start' }}
    </button>

    <div v-if="ec2Role" class="role-info">
      <h3>EC2 Role: {{ ec2Role }}</h3>
      <p>Authentication successful. You can now use the application.</p>
    </div>

    <div v-if="temporaryToken">
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
              :systemPrompt="systemPrompt"
              :awsCredentials="{
                region: awsRegion,
                accessKeyId: '',
                secretAccessKey: ''
              }"
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

// Get backend URL from config with debug logging
const BACKEND_URL = window.configs?.BACKEND_URL
console.log('Config object:', window.configs)
console.log('Using backend URL:', BACKEND_URL)

if (!BACKEND_URL) {
  console.error('Backend URL not found in config!')
}

export default {
  name: 'InputForm',
  components: {
    AudioRecorder,
  },
  created() {
    console.log('Component created with backend URL:', BACKEND_URL)
  },
  data() {
    return {
      s3AudioFileUrl: '',
      systemPrompt: '',
      transcriptionResult: '',
      bedrockResult: '',
      transcriptionMode: 'realtime',
      status: 'idle',
      s3Status: 'idle',
      error: null,
      ec2Role: null,
      temporaryToken: null,
      isFetchingRole: false,
      awsRegion: null
    }
  },
  methods: {
    async fetchEC2Role() {
      this.isFetchingRole = true
      this.error = null
      try {
        const response = await fetch(`${BACKEND_URL}/get_ec2_role`, {
          method: 'GET'
        })
        if (response.ok) {
          const result = await response.json()
          this.ec2Role = result.role
          this.temporaryToken = result.token
          this.awsRegion = result.region
          console.log('EC2 Role:', this.ec2Role)
          console.log('Temporary Token:', this.temporaryToken)
          console.log('AWS Region:', this.awsRegion)
        } else {
          const errorData = await response.json()
          throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`)
        }
      } catch (error) {
        console.error('Error fetching EC2 role:', error)
        if (error.message.includes("Failed to connect to instance metadata service")) {
          this.error = "Failed to connect to the EC2 instance metadata service. Please ensure the application is running on an EC2 instance."
        } else if (error.message.includes("No IAM role found")) {
          this.error = "No IAM role found. Please ensure the EC2 instance has an IAM role attached with the necessary permissions."
        } else if (error.message.includes("Timeout")) {
          this.error = "Timeout while fetching EC2 role. Please check your network connection and try again."
        } else {
          this.error = `Error fetching EC2 role: ${error.message}. Please ensure the application is running on an EC2 instance with the correct IAM role attached.`
        }
      } finally {
        this.isFetchingRole = false
      }
    },
    async submitS3Transcription() {
      if (!this.temporaryToken) {
        this.error = "Please fetch the EC2 role first."
        return
      }
      this.s3Status = 'matching'
      this.transcriptionResult = ''
      this.bedrockResult = ''
      this.error = null

      try {
        const response = await fetch(`${BACKEND_URL}/transcribe`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.temporaryToken}`
          },
          body: JSON.stringify({
            s3_audio_url: this.s3AudioFileUrl,
            system_prompt: this.systemPrompt
          })
        })

        if (response.ok) {
          const result = await response.json()
          this.transcriptionResult = result.transcript
          this.bedrockResult = result.bedrock_claude_result
          this.s3Status = 'matched'
        } else {
          const errorData = await response.json()
          throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`)
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
      if (!this.temporaryToken) {
        this.error = "Please fetch the EC2 role first."
        return
      }
      try {
        const response = await fetch(`${BACKEND_URL}/bedrock`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.temporaryToken}`
          },
          body: JSON.stringify({
            transcript: transcription,
            system_prompt: this.systemPrompt
          })
        })
        if (response.ok) {
          const result = await response.json()
          this.bedrockResult = result.bedrock_result
        } else {
          const errorData = await response.json()
          throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`)
        }
      } catch (error) {
        console.error('Error calling Bedrock:', error)
        this.error = `Error calling Bedrock: ${error.message}`
      }
    }
  }
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
