<template>
  <div class="input-form">
    <!-- Previous template content remains the same until the submit button -->
    <button @click="submitS3Transcription" 
      :disabled="s3Status === 'matching' || !selectedFile || !s3AudioFileUrl || !systemPrompt || !selectedModel" 
      class="btn btn-primary">
      {{ s3Status === 'matching' ? 'Processing...' : 'Submit' }}
    </button>
    <!-- Rest of the template remains the same -->
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
    this.loadSupportedModels()
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
      selectedModel: '' // Changed back to empty string as initial value
    }
  },
  watch: {
    // Add watchers for debugging
    selectedModel(newVal) {
      console.log('selectedModel changed:', newVal)
    },
    selectedFile(newVal) {
      console.log('selectedFile changed:', newVal ? newVal.name : 'null')
    },
    s3AudioFileUrl(newVal) {
      console.log('s3AudioFileUrl changed:', newVal)
    },
    systemPrompt(newVal) {
      console.log('systemPrompt changed:', newVal)
    }
  },
  methods: {
    async loadSupportedModels() {
      try {
        console.log('Loading models configuration...')
        const response = await fetch('/shared/config/models_config.json')
        if (response.ok) {
          const config = await response.json()
          console.log('Loaded models:', config.supported_models)
          this.supportedModels = config.supported_models
          
          // Set default selected model to the first model in the list
          const firstModelKey = Object.keys(this.supportedModels)[0]
          if (firstModelKey) {
            console.log('Setting default model:', firstModelKey)
            this.selectedModel = firstModelKey
          } else {
            console.warn('No models found in configuration')
          }
        } else {
          console.error('Failed to load models configuration')
          // Fallback to fetch from original location if shared config fails
          const fallbackResponse = await fetch('/models_config.json')
          if (fallbackResponse.ok) {
            const config = await fallbackResponse.json()
            console.log('Loaded models from fallback:', config.supported_models)
            this.supportedModels = config.supported_models
            const firstModelKey = Object.keys(this.supportedModels)[0]
            if (firstModelKey) {
              console.log('Setting default model from fallback:', firstModelKey)
              this.selectedModel = firstModelKey
            } else {
              console.warn('No models found in fallback configuration')
            }
          } else {
            console.error('Failed to load models configuration from fallback location')
          }
        }
      } catch (error) {
        console.error('Error loading models configuration:', error)
      }
    },
    // Rest of the methods remain the same
  }
}
</script>

<style scoped>
/* Previous styles remain the same */
</style>
