<template>
  <div class="audio-recorder">
    <button @click="startRecording" :disabled="isRecording || isStopping" class="btn btn-primary">Start Recording</button>
    <button @click="stopRecording" :disabled="!isRecording || isStopping" class="btn btn-secondary">Stop Recording</button>
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script>
import { TranscribeStreamingClient, StartStreamTranscriptionCommand } from "@aws-sdk/client-transcribe-streaming";

export default {
  name: 'AudioRecorder',
  props: {
    awsCredentials: {
      type: Object,
      required: true
    },
    systemPrompt: {
      type: String,
      required: true
    },
    selectedModel: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      isRecording: false,
      isStopping: false,  // 新增状态标志
      transcription: '',
      transcribeClient: null,
      error: null,
      audioContext: null,
      mediaStream: null,
      audioInput: null,
      processor: null,
      finalTranscription: '',
      transcriptionBuffer: [],
      lastProcessedIndex: 0
    }
  },
  methods: {
    cleanTranscription(transcript) {
      // Remove punctuation, convert to uppercase, and trim
      const cleanedTranscript = transcript
        .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, '')
        .toUpperCase()
        .trim();

      // Split into words and remove duplicates while preserving order
      const words = cleanedTranscript.split(/\s+/);
      const uniqueWords = [];
      const seenWords = new Set();

      for (const word of words) {
        if (!seenWords.has(word)) {
          uniqueWords.push(word);
          seenWords.add(word);
        }
      }

      return uniqueWords.join(' ');
    },

    async startRecording() {
      if (this.isRecording || this.isStopping) return;  // 防止重复启动
      
      try {
        this.error = null;
        this.transcription = '';
        this.finalTranscription = '';
        this.transcriptionBuffer = [];
        this.lastProcessedIndex = 0;
        
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error("Your browser doesn't support audio recording");
        }

        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        this.audioInput = this.audioContext.createMediaStreamSource(this.mediaStream);
        this.processor = this.audioContext.createScriptProcessor(1024, 1, 1);

        this.audioInput.connect(this.processor);
        this.processor.connect(this.audioContext.destination);

        this.isRecording = true;
        this.$emit('recordingStarted');

        // Initialize AWS Transcribe client with all credentials
        this.transcribeClient = new TranscribeStreamingClient({
          region: this.awsCredentials.region,
          credentials: {
            accessKeyId: this.awsCredentials.accessKeyId,
            secretAccessKey: this.awsCredentials.secretAccessKey,
            sessionToken: this.awsCredentials.sessionToken
          },
        });

        // Start transcription
        const command = new StartStreamTranscriptionCommand({
          LanguageCode: "en-US",
          MediaSampleRateHertz: this.audioContext.sampleRate,
          MediaEncoding: "pcm",
          AudioStream: this.audioStreamGenerator(),
        });

        const response = await this.transcribeClient.send(command);

        for await (const event of response.TranscriptResultStream) {
          if (event.TranscriptEvent && event.TranscriptEvent.Transcript) {
            const results = event.TranscriptEvent.Transcript.Results;
            if (results && results.length > 0 && results[0].Alternatives && results[0].Alternatives.length > 0) {
              const transcript = results[0].Alternatives[0].Transcript.trim();
              
              // Only process if the transcript is new
              if (transcript && !this.transcriptionBuffer.includes(transcript)) {
                this.transcriptionBuffer.push(transcript);
                
                // Keep only the last few transcripts to prevent memory bloat
                if (this.transcriptionBuffer.length > 5) {
                  this.transcriptionBuffer.shift();
                }

                // Update transcription with unique words
                this.transcription = this.cleanTranscription(
                  this.transcriptionBuffer.join(' ')
                );

                this.$emit('transcriptionUpdate', this.transcription);
              }
            }
          }
        }
      } catch (error) {
        console.error('Error starting recording:', error);
        this.error = `Error starting recording: ${error.message}`;
        this.cleanupResources();  // 使用新的清理方法
      }
    },

    // 新增资源清理方法
    async cleanupResources() {
      if (this.processor) {
        this.processor.disconnect();
        this.processor = null;
      }
      if (this.audioInput) {
        this.audioInput.disconnect();
        this.audioInput = null;
      }
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach(track => track.stop());
        this.mediaStream = null;
      }
      if (this.audioContext) {
        await this.audioContext.close();
        this.audioContext = null;
      }
      if (this.transcribeClient) {
        await this.transcribeClient.destroy();
        this.transcribeClient = null;
      }
    },

    async stopRecording() {
      if (!this.isRecording || this.isStopping) return;  // 防止重复停止
      
      try {
        this.isStopping = true;  // 设置停止标志
        this.isRecording = false;
        
        await this.cleanupResources();  // 使用新的清理方法
        
        // Clean and store the final transcription
        this.finalTranscription = this.cleanTranscription(this.transcription);
        this.$emit('recordingStopped', this.finalTranscription);

        // Call Bedrock with the final transcription and selected model
        await this.callBedrock(this.finalTranscription);
      } catch (error) {
        console.error('Error stopping recording:', error);
        this.error = `Error stopping recording: ${error.message}`;
      } finally {
        this.isStopping = false;  // 重置停止标志
      }
    },

    async *audioStreamGenerator() {
      const self = this;
      let audioBuffer = [];

      this.processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        audioBuffer.push(new Float32Array(inputData));
      };

      while (this.isRecording) {
        if (audioBuffer.length > 0) {
          const audioData = audioBuffer.shift();
          const pcmBuffer = this.float32ToInt16(audioData);
          yield { AudioEvent: { AudioChunk: pcmBuffer } };
        }
        await new Promise(resolve => setTimeout(resolve, 10));
      }
    },

    float32ToInt16(float32Array) {
      const int16Array = new Int16Array(float32Array.length);
      for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]));
        int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      return Buffer.from(int16Array.buffer);
    },

    async callBedrock(transcription) {
      if (!transcription.trim()) {
        console.log('Empty transcription, skipping Bedrock call');
        return;
      }

      try {
        // Use window.configs.BACKEND_URL instead of process.env
        const response = await fetch(`${window.configs.BACKEND_URL}/bedrock`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.awsCredentials.sessionToken}`
          },
          body: JSON.stringify({
            transcript: transcription,
            system_prompt: this.systemPrompt,
            model_name: this.selectedModel
          })
        });

        if (response.ok) {
          const result = await response.json();
          this.$emit('bedrockResult', result.bedrock_result);
        } else {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Error: ${response.status} - ${response.statusText}`);
        }
      } catch (error) {
        console.error('Error calling Bedrock:', error);
        this.error = `Error calling Bedrock: ${error.message}`;
      }
    },
  },
}
</script>

<style scoped>
.audio-recorder {
  margin-bottom: 20px;
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

.error-message {
  color: red;
  margin-top: 10px;
}
</style>
