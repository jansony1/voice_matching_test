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
      currentTranscript: '',
      resultId: null
    }
  },
  methods: {
    generateUUID() {
      return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
      });
    },

    processTranscript(results) {
      if (!results || results.length === 0) return;

      const result = results[0];
      if (!result.Alternatives || result.Alternatives.length === 0) return;

      const transcript = result.Alternatives[0].Transcript;
      
      // 只处理非空的转录结果
      if (!transcript.trim()) return;

      // 如果是新的结果ID，重置当前转录
      if (this.resultId !== result.ResultId) {
        this.resultId = result.ResultId;
        this.currentTranscript = '';
      }

      // 根据IsPartial标志处理结果
      if (result.IsPartial) {
        // 部分结果：更新当前转录但不更新最终转录
        this.currentTranscript = transcript.trim();
        // 发出更新事件但使用临时结果
        this.$emit('transcriptionUpdate', this.currentTranscript);
      } else {
        // 最终结果：更新当前转录和最终转录
        this.currentTranscript = transcript.trim();
        
        // 如果是新的完整结果，添加到最终转录
        if (this.currentTranscript && this.currentTranscript !== this.transcription) {
          this.transcription = this.currentTranscript;
          // 发出更新事件使用最终结果
          this.$emit('transcriptionUpdate', this.transcription);
        }
      }
    },

    async startRecording() {
      if (this.isRecording || this.isStopping) return;
      
      try {
        this.error = null;
        this.transcription = '';
        this.currentTranscript = '';
        this.resultId = null;
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
          PartialResultsStability: "high"
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
        
        // 使用最终的完整转录
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
