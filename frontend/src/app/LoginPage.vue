<script setup lang="ts">
import { PhSpinnerGap } from '@phosphor-icons/vue'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePreferences } from '@/stores/preferences'
import { useSession } from '@/stores/session'
import BrandHeader from './BrandHeader.vue'

const session = useSession()
const prefs = usePreferences()
const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const remember = ref(true)
const error = ref('')
const busy = ref(false)

onMounted(() => void prefs.loadBranding())

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await session.login(username.value, password.value, remember.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') && !route.query.next.startsWith('//') ? route.query.next : '/'
    await router.replace(next)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    password.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="login">
    <BrandHeader compact />
    <form class="card glass" @submit.prevent="submit">
      <h2>{{ $t('Connexion') }}</h2>
      <label class="field">
        <span>{{ $t('Identifiant') }}</span>
        <input v-model="username" class="input" autocomplete="username" autocapitalize="none" spellcheck="false" required />
      </label>
      <label class="field">
        <span>{{ $t('Mot de passe') }}</span>
        <input v-model="password" class="input" type="password" autocomplete="current-password" required />
      </label>
      <label class="check">
        <input v-model="remember" type="checkbox" />
        {{ $t('Rester connecté sur cet appareil (30 jours)') }}
      </label>
      <p v-if="error" class="error-text" role="alert">{{ error }}</p>
      <button class="btn primary" type="submit" :disabled="busy">
        <PhSpinnerGap v-if="busy" class="spin" :size="16" /> {{ $t('Se connecter') }}
      </button>
    </form>
  </main>
</template>

<style scoped>
.login {
  min-height: 100dvh;
  display: grid;
  place-content: center;
  justify-items: center;
  padding: 24px 16px;
}
.card {
  width: min(380px, calc(100vw - 32px));
  padding: 26px;
  display: grid;
  gap: 16px;
}
h2 {
  font-size: 20px;
  font-weight: 650;
}
.btn {
  height: 44px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
