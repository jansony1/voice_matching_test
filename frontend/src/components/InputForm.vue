<template>
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
      <div class="auth-mode-selection">
        <h3>Select Authentication Mode</h3>
        <div class="auth-mode-buttons">
          <button 
            @click="authMode = 'ec2'" 
            class="btn" 
            :class="{ 'btn-primary': authMode === 'ec2', 'btn-secondary': authMode !== 'ec2' }"
          >
            EC2 Role
          </button>
          <button 
            @click="authMode = 'manual'" 
            class="btn" 
            :class="{ 'btn-primary': authMode === 'manual', 'btn-secondary': authMode !== 'manual' }"
          >
            Manual Credentials
          </button>
        </div>
      </div>

      <!-- EC2 Role Mode -->
      <div v-if="authMode === 'ec2'" class="auth-section">
        <button @click="fetchEC2Role" class="btn btn-primary" :disabled="isFetchingRole">
          {{ isFetchingRole ? 'Fetching EC2 Role...' : 'Get EC2 Role and Start' }}
        </button>
      </div>

      <!-- Manual Credentials Mode -->
      <div v-if="authMode === 'manual'" class="auth-section">
        <div class="form-group">
          <label class="highlight-label">Access Key ID</label>
          <input 
            type="text" 
            v-model="manualCredentials.accessKeyId" 
            class="form-control"
            placeholder="Enter AWS Access Key ID"
          />
        </div>
        <div class="form-group">
          <label class="highlight-label">Secret Access Key</label>
          <input 
            type="password" 
            v-model="manualCredentials.secretAccessKey" 
            class="form-control"
            placeholder="Enter AWS Secret Access Key"
          />
        </div>
        <div class="form-group">
          <label class="highlight-label">Region</label>
          <input 
            type="text" 
            v-model="manualCredentials.region" 
            class="form-control"
            placeholder="Enter AWS Region (e.g., us-east-1)"
          />
        </div>
        <button @click="setManualCredentials" class="btn btn-primary" :disabled="!isManualCredentialsValid">
          Set Credentials and Start
        </button>
      </div>

      <div v-if="ec2Role || manualCredentialsSet" class="role-info">
        <template v-if="authMode === 'ec2'">
          <h3>EC2 Role: {{ ec2Role }}</h3>
        </template>
        <template v-else>
          <h3>Manual Credentials</h3>
        </template>
        <p>Authentication successful. You can now use the application.</p>
      </div>

      <div v-if="awsCredentials.sessionToken || manualCredentialsSet">
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
              <label class="highlight-label">Dict Upld for Expansion</label>
              <input 
                type="file" 
                @change="handleJsonFileChange" 
                accept=".json"
                class="form-control"
                id="jsonFileInput"
              />
              <small class="file-hint">Only Sonnet3.5 was Supported</small>
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
          <li class="nav-item">
            <a class="nav-link" :class="{ active: transcriptionMode === 'text' }" href="#" @click.prevent="transcriptionMode = 'text'">Text Input</a>
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

          <div class="tab-pane" :class="{ 'active': transcriptionMode === 'text' }">
            <div class="text-input-transcription">
              <div class="form-group">
                <label for="textInput" class="highlight-label">Text Input</label>
                <textarea 
                  id="textInput" 
                  v-model="textInput" 
                  placeholder="Enter your text here" 
                  class="form-control"
                  rows="4"
                ></textarea>
              </div>
              <button @click="submitTextInput" :disabled="!systemPrompt || !textInput" class="btn btn-primary">
                {{ textStatus === 'matching' ? 'Processing...' : 'Submit' }}
              </button>
              <div v-if="textStatus === 'matched'" class="status-text">
                Match Result
              </div>
              <div v-if="bedrockResult" class="bedrock-result">
                <h3>Bedrock Inference Result</h3>
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
      textInput: '',
      textStatus: 'idle',
      authMode: 'ec2',
      manualCredentials: {
        accessKeyId: '',
        secretAccessKey: '',
        region: ''
      },
      manualCredentialsSet: false,
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
            'Authorization': this.authMode === 'ec2' ? 
              `Bearer ${this.awsCredentials.sessionToken}` : 
              `Basic ${btoa(`${this.awsCredentials.accessKeyId}:${this.awsCredentials.secretAccessKey}`)}`
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
    async setManualCredentials() {
      if (!this.isManualCredentialsValid) {
        this.error = "Please fill in all credential fields"
        return
      }

      try {
        this.awsCredentials = {
          accessKeyId: this.manualCredentials.accessKeyId,
          secretAccessKey: this.manualCredentials.secretAccessKey,
          region: this.manualCredentials.region,
          sessionToken: null // Not needed for manual credentials
        }
        this.manualCredentialsSet = true
        this.error = null
      } catch (error) {
        console.error('Error setting manual credentials:', error)
        this.error = `Error setting credentials: ${error.message}`
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
          'Authorization': this.authMode === 'ec2' ? 
              `Bearer ${this.awsCredentials.sessionToken}` : 
              `Basic ${btoa(`${this.awsCredentials.accessKeyId}:${this.awsCredentials.secretAccessKey}`)}`
        },
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`)
      }

      return await response.json()
    },
    async submitTextInput() {
      if (!this.awsCredentials.accessKeyId) {
        this.error = "Please set AWS credentials first."
        return
      }
      if (!this.textInput || !this.systemPrompt) {
        this.error = "Please enter text and a system prompt."
        return
      }

      this.textStatus = 'matching'
      this.bedrockResult = ''
      this.error = null

      try {
        const response = await fetch(`${BACKEND_URL}/bedrock`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': this.authMode === 'ec2' ? 
              `Bearer ${this.awsCredentials.sessionToken}` : 
              `Basic ${btoa(`${this.awsCredentials.accessKeyId}:${this.awsCredentials.secretAccessKey}`)}`
          },
          body: JSON.stringify({
            transcript: this.textInput,
            system_prompt: this.systemPrompt,
            model_name: this.selectedModel
          })
        });

        if (response.ok) {
          const result = await response.json()
          this.bedrockResult = result.bedrock_result
          this.textStatus = 'matched'
        } else {
          const errorData = await response.json()
          throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`)
        }
      } catch (error) {
        console.error('Error in text processing:', error)
        this.error = `Error: ${error.message}`
        this.textStatus = 'idle'
      }
    },

    async submitS3Transcription() {
      if (!this.awsCredentials.accessKeyId) {
        this.error = "Please set AWS credentials first."
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
            'Authorization': this.authMode === 'ec2' ? 
              `Bearer ${this.awsCredentials.sessionToken}` : 
              `Basic ${btoa(`${this.awsCredentials.accessKeyId}:${this.awsCredentials.secretAccessKey}`)}`
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
  },
  computed: {
    isManualCredentialsValid() {
      return this.manualCredentials.accessKeyId &&
             this.manualCredentials.secretAccessKey &&
             this.manualCredentials.region
    }
  }
}
</script>

<style scoped>
.input-form {
  max-width: 1000px;
  margin: 0 auto;
  padding: 30px;
  background-color: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
}

/* Login form styles */
.login-form {
  max-width: 440px;
  margin: 40px auto;
  padding: 32px;
  background-color: #ffffff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
}

.login-form h2 {
  text-align: center;
  margin-bottom: 24px;
  color: #2D8CFF;
  font-size: 24px;
  font-weight: 600;
}

.form-group {
  margin-bottom: 24px;
}

.highlight-label {
  font-weight: 500;
  color: #232333;
  font-size: 14px;
  margin-bottom: 8px;
  display: block;
}

.form-control {
  width: 100%;
  padding: 12px;
  border: 1px solid #E5E5E5;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
  background-color: #FAFAFA;
}

.form-control:focus {
  border-color: #2D8CFF;
  box-shadow: 0 0 0 2px rgba(45, 140, 255, 0.2);
  outline: none;
}

.input-group {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background-color: #2D8CFF;
  color: #fff;
}

.btn-primary:hover {
  background-color: #2478DB;
}

.btn-secondary {
  background-color: #F5F5F5;
  color: #232333;
  border: 1px solid #E5E5E5;
}

.btn-secondary:hover {
  background-color: #EAEAEA;
}

.btn:disabled {
  background-color: #E5E5E5;
  color: #999999;
  cursor: not-allowed;
}

/* Variation controls */
.variation-controls {
  background-color: #FAFAFA;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
}

.file-upload-container {
  width: 100%;
}

.generate-button-container {
  margin-top: 16px;
}

.file-hint {
  color: #666666;
  font-size: 12px;
  margin-top: 8px;
}

.nav-tabs {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 32px 0 24px;
  border-bottom: 1px solid #E5E5E5;
  gap: 4px;
}

.nav-item {
  margin-bottom: -1px;
}

.nav-link {
  display: block;
  padding: 12px 24px;
  text-decoration: none;
  color: #666666;
  font-weight: 500;
  font-size: 14px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.nav-link:hover {
  color: #2D8CFF;
}

.nav-link.active {
  color: #2D8CFF;
  border-bottom-color: #2D8CFF;
  background-color: transparent;
}

.tab-content {
  background-color: #FFFFFF;
  border-radius: 8px;
  padding: 24px;
}

.tab-pane {
  display: none;
}

.tab-pane.active {
  display: block;
}

.status-text {
  margin: 20px 0;
  font-weight: 500;
  color: #2D8CFF;
  font-size: 14px;
}

.transcription-result, .bedrock-result {
  margin-top: 24px;
  background-color: #FAFAFA;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #E5E5E5;
}

.transcription-result h3, .bedrock-result h3 {
  color: #232333;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
  color: #333333;
  background-color: #FFFFFF;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #E5E5E5;
}

.error-message {
  color: #DC3545;
  font-size: 14px;
  margin-top: 12px;
  padding: 12px;
  background-color: #FFF5F5;
  border-radius: 6px;
  border: 1px solid #FFE5E5;
}

.upload-progress {
  margin: 16px 0;
  color: #2D8CFF;
  font-weight: 500;
  font-size: 14px;
}

/* Auth mode selection styles */
.auth-mode-selection {
  margin-bottom: 32px;
  text-align: center;
}

.auth-mode-selection h3 {
  color: #232333;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 16px;
}

.auth-mode-buttons {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.auth-section {
  max-width: 440px;
  margin: 0 auto 32px;
  padding: 24px;
  background-color: #FAFAFA;
  border-radius: 12px;
  border: 1px solid #E5E5E5;
}

/* Role info styles */
.role-info {
  background-color: #F0F9FF;
  border-radius: 8px;
  padding: 16px;
  margin: 20px 0;
}

.role-info h3 {
  color: #2D8CFF;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.role-info p {
  color: #666666;
  font-size: 14px;
  margin: 0;
}
</style>
