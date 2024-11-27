<template>
  <div class="audio-recorder">
    <button @click="startRecording" :disabled="isRecording" class="btn btn-primary">Start Recording</button>
    <button @click="stopRecording" :disabled="!isRecording" class="btn btn-secondary">Stop Recording</button>
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
    }
  },
  data() {
    return {
      isRecording: false,
      transcription: '',
      transcribeClient: null,
      error: null,
      audioContext: null,
      mediaStream: null,
      audioInput: null,
      processor: null,
    }
  },
  methods: {
    async startRecording() {
      try {
        this.error = null;
        this.transcription = '';
        
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

        // Initialize AWS Transcribe client
        this.transcribeClient = new TranscribeStreamingClient({
          region: this.awsCredentials.region,
          credentials: {
            accessKeyId: this.awsCredentials.accessKeyId,
            secretAccessKey: this.awsCredentials.secretAccessKey,
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
              const transcript = results[0].Alternatives[0].Transcript;
              this.transcription += transcript + ' ';
              this.$emit('transcriptionUpdate', this.transcription);
            }
          }
        }
      } catch (error) {
        console.error('Error starting recording:', error);
        this.error = `Error starting recording: ${error.message}`;
        await this.stopRecording();
      }
    },
    async stopRecording() {
      try {
        this.isRecording = false;
        
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
        
        this.$emit('recordingStopped', this.transcription);
      } catch (error) {
        console.error('Error stopping recording:', error);
        this.error = `Error stopping recording: ${error.message}`;
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
