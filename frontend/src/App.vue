<template>
  <div id="app">
    <InputForm>
      <SpeechTranscription
        :transcriptionMode="transcriptionMode"
        :transcriptionResult="transcriptionResult"
        :result="result"
      />
    </InputForm>
  </div>
</template>

<script>
import InputForm from './components/InputForm.vue'
import SpeechTranscription from './components/SpeechTranscription.vue'

export default {
  name: 'App',
  components: {
    InputForm,
    SpeechTranscription,
  },
  data() {
    return {
      transcriptionMode: 'realtime',
      transcriptionResult: '',
      result: null,
    }
  },
  mounted() {
    window.addEventListener('message', (event) => {
      if (event.data.type === 'transcriptionMode') {
        this.transcriptionMode = event.data.value
      } else if (event.data.type === 'transcriptionResult') {
        this.transcriptionResult = event.data.value
      } else if (event.data.type === 'result') {
        this.result = event.data.value
      }
    })
  },
}
</script>
