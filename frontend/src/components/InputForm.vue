<template>
  <!-- Template remains unchanged -->
  <div class="input-form">
    <!-- Login Form -->
    <div v-if="!isLoggedIn" class="login-form">
      <h2>Login Required</h2>
      <div class="form-group">
        <label for="username">Username</label>
        <input 
          type="text" 
          id="username" 
          v-model="loginForm.username" 
          class="form-control"
          placeholder="Enter username"
        />
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input 
          type="password" 
          id="password" 
          v-model="loginForm.password" 
          class="form-control"
          placeholder="Enter password"
        />
      </div>
      <button @click="handleLogin" class="btn btn-primary" :disabled="isLoggingIn">
        {{ isLoggingIn ? 'Logging in...' : 'Login' }}
      </button>
      <div v-if="loginError" class="error-message">
        {{ loginError }}
      </div>
    </div>

    <!-- Main Content (only shown after login) -->
    <div v-else>
      <button @click="fetchEC2Role" class="btn btn-primary" :disabled="isFetchingRole">
        {{ isFetchingRole ? 'Fetching EC2 Role...' : 'Get EC2 Role and Start' }}
      </button>

      <div v-if="ec2Role" class="role-info">
        <h3>EC2 Role: {{ ec2Role }}</h3>
        <p>Authentication successful. You can now use the application.</p>
      </div>

      <div v-if="awsCredentials.sessionToken">
        <div class="form-group">
          <label for="modelSelect" class="highlight-label">Select Model</label>
          <select id="modelSelect" v-model="selectedModel" class="form-control">
            <option v-for="(model, key) in supportedModels" :key="key" :value="key">
              {{ model.display_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label for="systemPrompt" class="highlight-label">System Prompt</label>
          <textarea id="systemPrompt" v-model="systemPrompt" placeholder="Enter system prompt" class="form-control"></textarea>
          
          <!-- Variation controls -->
          <div class="variation-controls">
            <div class="file-upload-container">
              <label class="highlight-label">Upload JSON File</label>
              <input 
                type="file" 
                @change="handleJsonFileChange" 
                accept=".json"
                class="form-control"
                id="jsonFileInput"
              />
              <small class="file-hint">Upload JSON file for variation</small>
            </div>
            <div class="generate-button-container">
              <button @click="generateVariation" class="btn btn-secondary" :disabled="!jsonFile">
                Generate Variation
              </button>
            </div>
          </div>
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
                :awsCredentials="awsCredentials"
                :selectedModel="selectedModel"
                @transcriptionUpdate="handleTranscriptionUpdate"
                @recordingStopped="handleRecordingStopped"
                @recordingStarted="handleRecordingStarted"
                @bedrockResult="handleBedrockResult"
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
                <label for="audioFile" class="highlight-label">Audio File</label>
                <input 
                  type="file" 
                  id="audioFile" 
                  @change="handleFileChange" 
                  accept="audio/*"
                  class="form-control"
                />
              </div>
              <div class="form-group">
                <label for="s3AudioFileUrl" class="highlight-label">S3 Audio File URL</label>
                <input type="text" id="s3AudioFileUrl" v-model="s3AudioFileUrl" placeholder="Enter S3 destination path (e.g., s3://bucket-name/path/file.mp3)" class="form-control" />
              </div>
              <button @click="submitS3Transcription" :disabled="!systemPrompt || !selectedFile || !s3AudioFileUrl" class="btn btn-primary">
                {{ s3Status === 'matching' ? 'Processing...' : 'Submit' }}
              </button>
              <div v-if="uploadProgress > 0 && uploadProgress < 100" class="upload-progress">
                Uploading: {{ uploadProgress }}%
              </div>
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
    </div>

    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script>
import './InputForm.css'
import AudioRecorder from './AudioRecorder.vue'

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
    this.loadSupportedModels()
  },
  data() {
    return {
      isLoggedIn: false,
      isLoggingIn: false,
      loginError: null,
      loginForm: {
        username: '',
        password: ''
      },
      s3AudioFileUrl: '',
      systemPrompt: '',
      transcriptionResult: '',
      bedrockResult: '',
      transcriptionMode: 'realtime',
      status: 'idle',
      s3Status: 'idle',
      error: null,
      ec2Role: null,
      isFetchingRole: false,
      selectedFile: null,
      uploadProgress: 0,
      awsCredentials: {
        region: null,
        accessKeyId: '',
        secretAccessKey: '',
        sessionToken: ''
      },
      supportedModels: {},
      selectedModel: '',
      jsonFile: null
    }
  },
  methods: {
    async handleLogin() {
      if (!this.loginForm.username || !this.loginForm.password) {
        this.loginError = 'Please enter both username and password'
        return
      }

      this.isLoggingIn = true
      this.loginError = null

      try {
        const response = await fetch(`${BACKEND_URL}/login`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: this.loginForm.username,
            password: this.loginForm.password
          })
        })

        if (response.ok) {
          this.isLoggedIn = true
          this.loginError = null
        } else {
          const error = await response.json()
          throw new Error(error.detail || 'Login failed')
        }
      } catch (error) {
        console.error('Login error:', error)
        this.loginError = error.message
      } finally {
        this.isLoggingIn = false
      }
    },
    handleJsonFileChange(event) {
      const file = event.target.files[0]
      if (file) {
        if (!file.name.endsWith('.json')) {
          this.error = 'Please upload a JSON file'
          event.target.value = '' // Reset file input
          this.jsonFile = null
          return
        }
        this.jsonFile = file
        this.error = null
      } else {
        this.jsonFile = null
      }
    },
    async generateVariation() {
      if (!this.jsonFile) {
        this.error = 'Please upload a JSON file'
        return
      }

      // Create an AbortController with a 15-minute timeout (extended from 10)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 15 * 60 * 1000) // 15 minutes

      try {
        const fileContent = await this.jsonFile.text()
        let jsonData
        try {
          jsonData = JSON.parse(fileContent)
        } catch (e) {
          this.error = 'Invalid JSON format'
          return
        }

        const response = await fetch(`${BACKEND_URL}/generate_variation`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.awsCredentials.sessionToken}`
          },
          body: JSON.stringify({
            json_data: jsonData
          }),
          signal: controller.signal // Add the abort signal
        })

        // Clear the timeout if the request completes successfully
        clearTimeout(timeoutId)

        // Check for non-JSON responses
        const contentType = response.headers.get('content-type')
        if (!contentType || !contentType.includes('application/json')) {
          const errorText = await response.text()
          throw new Error(`Unexpected response: ${errorText}`)
        }

        if (response.ok) {
          const result = await response.json()
          this.systemPrompt = result.bedrock_result
          this.error = null
        } else {
          const errorData = await response.json()
          throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`)
        }
      } catch (error) {
        // Handle specific error scenarios
        if (error.name === 'AbortError') {
          this.error = 'Request timed out. The operation took longer than 15 minutes.'
        } else if (error.message.includes('Unexpected token')) {
          this.error = 'Received an invalid response from the server. Please try again.'
          console.error('Unexpected response:', error)
        } else if (error.message.includes('504')) {
          this.error = 'Gateway Timeout. The server took too long to respond. Please try again later.'
        } else {
          console.error('Error generating variation:', error)
          this.error = `Error generating variation: ${error.message}`
        }
      }
    },  
      // Rest of the methods remain unchanged
    handleFileChange(event) {
      const file = event.target.files[0]
      if (file) {
        this.selectedFile = file
        console.log('File selected:', file.name)
      } else {
        this.selectedFile = null
        console.log('No file selected')
      }
    },
    async loadSupportedModels() {
      try {
        const response = await fetch('/shared/config/models_config.json')
        if (response.ok) {
          const config = await response.json()
          this.supportedModels = config.supported_models
          
          // Set default selected model to the first model in the list
          const firstModelKey = Object.keys(this.supportedModels)[0]
          this.selectedModel = firstModelKey
        } else {
          console.error('Failed to load models configuration')
          // Fallback to fetch from original location if shared config fails
          const fallbackResponse = await fetch('/models_config.json')
          if (fallbackResponse.ok) {
            const config = await fallbackResponse.json()
            this.supportedModels = config.supported_models
            const firstModelKey = Object.keys(this.supportedModels)[0]
            this.selectedModel = firstModelKey
          } else {
            console.error('Failed to load models configuration from fallback location')
          }
        }
      } catch (error) {
        console.error('Error loading models configuration:', error)
      }
    },
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
          
          // Update AWS credentials
          this.awsCredentials = {
            region: result.region,
            accessKeyId: result.accessKeyId,
            secretAccessKey: result.secretAccessKey,
            sessionToken: result.sessionToken
          }

          console.log('EC2 Role:', this.ec2Role)
          console.log('AWS Region:', this.awsCredentials.region)
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
    async uploadFileToS3() {
      if (!this.selectedFile || !this.s3AudioFileUrl) {
        throw new Error('Please select a file and provide an S3 destination path')
      }

      const formData = new FormData()
      formData.append('file', this.selectedFile)
      formData.append('s3_path', this.s3AudioFileUrl)

      const response = await fetch(`${BACKEND_URL}/upload_to_s3`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.awsCredentials.sessionToken}`
        },
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`)
      }

      return await response.json()
    },
    async submitS3Transcription() {
      if (!this.awsCredentials.sessionToken) {
        this.error = "Please fetch the EC2 role first."
        return
      }
      if (!this.selectedFile || !this.s3AudioFileUrl || !this.systemPrompt) {
        this.error = "Please select a file, provide an S3 destination path, and enter a system prompt."
        return
      }

      this.s3Status = 'matching'
      this.transcriptionResult = ''
      this.bedrockResult = ''
      this.error = null
      this.uploadProgress = 0

      try {
        // First upload the file to S3
        console.log('Starting file upload to S3...')
        const uploadResult = await this.uploadFileToS3()
        this.uploadProgress = 100
        console.log('File uploaded successfully:', uploadResult)

        // Then proceed with transcription using the S3 URL from the upload result
        console.log('Starting transcription with S3 URL:', uploadResult.s3_url)
        const response = await fetch(`${BACKEND_URL}/transcribe`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.awsCredentials.sessionToken}`
          },
          body: JSON.stringify({
            s3_audio_url: uploadResult.s3_url,
            system_prompt: this.systemPrompt,
            model_name: this.selectedModel
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
        console.error('Error in S3 transcription process:', error)
        this.error = `Error: ${error.message}`
        this.s3Status = 'idle'
      }
    },
    handleTranscriptionUpdate(transcription) {
      this.transcriptionResult = transcription
      this.status = 'matching'
    },
    handleRecordingStopped(finalTranscription) {
      this.transcriptionResult = finalTranscription
      this.status = 'matched'
    },
    handleBedrockResult(result) {
      this.bedrockResult = result
    },
    handleRecordingStarted() {
      this.status = 'matching'
      this.transcriptionResult = ''
      this.bedrockResult = ''
    }
  }
}
</script>

<style scoped>
/* Previous styles remain unchanged */
.input-form {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

/* Login form styles */
.login-form {
  max-width: 400px;
  margin: 40px auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 5px;
  background-color: #f8f9fa;
}

.login-form h2 {
  text-align: center;
  margin-bottom: 20px;
  color: #007bff;
}

.form-group {
  margin-bottom: 20px;
}

.highlight-label {
  font-weight: bold;
  color: #007bff;
  font-size: 1.1em;
  margin-bottom: 8px;
  display: block;
  background-color: #f8f9fa;
  padding: 5px 10px;
  border-radius: 3px;
  border-left: 3px solid #007bff;
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

.btn-secondary {
  background-color: #6c757d;
  color: #fff;
}

.btn:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

/* Variation controls */
.variation-controls {
  display: flex;
  flex-direction: column;
  margin-top: 15px;
  gap: 15px;
}

.file-upload-container {
  width: 100%;
}

.generate-button-container {
  width: 100%;
  display: flex;
  justify-content: flex-start;
}

.file-hint {
  color: #6c757d;
  margin-top: 5px;
  display: block;
}

/* Rest of the styles remain unchanged */
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

.upload-progress {
  margin: 10px 0;
  color: #007bff;
  font-weight: bold;
}
</style>
