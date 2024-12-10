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
      isStopping: false,
      transcription: '',
      transcribeClient: null,
      error: null,
      audioContext: null,
      mediaStream: null,
      audioInput: null,
      processor: null,
      finalTranscription: '',
      partialTranscript: '',
      isPartial: false
    }
  },
  methods: {
    processTranscript(results) {
      if (!results || results.length === 0) return;

      const result = results[0];
      if (!result.Alternatives || result.Alternatives.length === 0) return;

      const transcript = result.Alternatives[0].Transcript.trim();
      const isPartial = !result.IsPartial;

      if (isPartial) {
        // 这是一个部分结果，更新部分转录
        this.partialTranscript = transcript;
      } else {
        // 这是一个最终结果，将其添加到完整转录中
        if (transcript) {
          // 只有当转录不为空时才处理
          const words = transcript.split(/\s+/);
          const lastTranscriptWords = this.transcription.split(/\s+/);
          
          // 检查新单词是否已经存在于最后的转录中
          const newWords = words.filter(word => !lastTranscriptWords.includes(word));
          
          if (newWords.length > 0) {
            // 只添加新的单词
            this.transcription = this.transcription
              ? `${this.transcription} ${newWords.join(' ')}`
              : newWords.join(' ');
          }
        }
        this.partialTranscript = ''; // 清除部分转录
      }

      // 发出更新事件
      this.$emit('transcriptionUpdate', this.transcription);
    },

    async startRecording() {
      if (this.isRecording || this.isStopping) return;
      
      try {
        this.error = null;
        this.transcription = '';
        this.partialTranscript = '';
        this.finalTranscription = '';
        
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

        this.transcribeClient = new TranscribeStreamingClient({
          region: this.awsCredentials.region,
          credentials: {
            accessKeyId: this.awsCredentials.accessKeyId,
            secretAccessKey: this.awsCredentials.secretAccessKey,
            sessionToken: this.awsCredentials.sessionToken
          },
        });

        const command = new StartStreamTranscriptionCommand({
          LanguageCode: "en-US",
          MediaSampleRateHertz: this.audioContext.sampleRate,
          MediaEncoding: "pcm",
          AudioStream: this.audioStreamGenerator(),
          EnablePartialResultsStabilization: true,
          PartialResultsStability: "HIGH"
        });

        const response = await this.transcribeClient.send(command);

        for await (const event of response.TranscriptResultStream) {
          if (event.TranscriptEvent && event.TranscriptEvent.Transcript) {
            this.processTranscript(event.TranscriptEvent.Transcript.Results);
          }
        }
      } catch (error) {
        console.error('Error starting recording:', error);
        this.error = `Error starting recording: ${error.message}`;
        this.cleanupResources();
      }
    },

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
      if (!this.isRecording || this.isStopping) return;
      
      try {
        this.isStopping = true;
        this.isRecording = false;
        
        await this.cleanupResources();
        
        // 清理并存储最终转录
        this.finalTranscription = this.transcription.trim();
        this.$emit('recordingStopped', this.finalTranscription);

        // 调用 Bedrock
        await this.callBedrock(this.finalTranscription);
      } catch (error) {
        console.error('Error stopping recording:', error);
        this.error = `Error stopping recording: ${error.message}`;
      } finally {
        this.isStopping = false;
      }
    },

    async *audioStreamGenerator() {
      const audioBuffer = [];

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
