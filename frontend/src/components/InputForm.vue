<template>
  <!-- Keep existing template -->
  <div class="input-form">
    <!-- ... rest of the template ... -->
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
    // Log configuration on component creation
    console.log('Component created with backend URL:', BACKEND_URL)
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
        console.log('Validating credentials with URL:', BACKEND_URL)
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
  }
}
</script>

<style scoped>
/* Keep existing styles */
</style>
