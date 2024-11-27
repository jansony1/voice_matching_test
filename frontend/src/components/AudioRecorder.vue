<template>
  <div class="audio-recorder">
    <button @click="startRecording" :disabled="isRecording" class="btn btn-primary">Start Recording</button>
    <button @click="stopRecording" :disabled="!isRecording" class="btn btn-secondary">Stop Recording</button>
    <div v-if="audioBlob">
      <audio :src="audioUrl" controls></audio>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AudioRecorder',
  data() {
    return {
      isRecording: false,
      mediaRecorder: null,
      audioChunks: [],
      audioBlob: null,
      audioUrl: null,
    }
  },
  methods: {
    startRecording() {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
          this.mediaRecorder = new MediaRecorder(stream)
          this.mediaRecorder.start()
          this.isRecording = true
          this.audioChunks = []

          this.mediaRecorder.addEventListener('dataavailable', event => {
            this.audioChunks.push(event.data)
            this.$emit('audioChunk', event.data)
          })

          this.mediaRecorder.addEventListener('stop', () => {
            this.audioBlob = new Blob(this.audioChunks)
            this.audioUrl = URL.createObjectURL(this.audioBlob)
          })
        })
        .catch(error => {
          console.error('Error accessing microphone:', error)
        })
    },
    stopRecording() {
      this.mediaRecorder?.stop()
      this.isRecording = false
      this.$emit('recordingStopped')
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
</style>
