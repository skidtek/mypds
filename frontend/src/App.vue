<script setup lang="ts">
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { setUnauthorizedHandler } from '@/api/client'
import { instantNav } from '@/app/transition'
import { usePreferences } from '@/stores/preferences'
import { useSession } from '@/stores/session'

const session = useSession()
const prefs = usePreferences()
const router = useRouter()

setUnauthorizedHandler(() => {
  session.set(null)
  if (router.currentRoute.value.name !== 'login') void router.replace({ name: 'login', query: { next: router.currentRoute.value.fullPath } })
})

watch(
  () => session.me?.username,
  async (user) => {
    if (user) await Promise.all([prefs.load(), prefs.loadBranding()])
  },
  { immediate: true },
)
</script>

<template>
  <div class="backdrop" aria-hidden="true" />
  <RouterView v-slot="{ Component }">
    <Transition name="page" :css="!instantNav">
      <component :is="Component" />
    </Transition>
  </RouterView>
</template>
