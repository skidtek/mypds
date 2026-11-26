<script setup lang="ts">
import { PhMagnifyingGlass, PhTrash, PhUploadSimple } from '@phosphor-icons/vue'
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { IconRef } from '@/api/types'
import GlassDialog from '@/design-system/components/GlassDialog.vue'
import { iconIndex, type SimpleIcon } from './icons'
import TileIcon from './TileIcon.vue'

const props = defineProps<{ initialQuery?: string }>()
const emit = defineEmits<{ close: []; pick: [icon: IconRef | null] }>()
const tab = ref<'simple' | 'upload'>('simple')
const q = ref(props.initialQuery ?? '')
const all = ref<SimpleIcon[]>([])
const uploads = ref<{ id: string; name: string }[]>([])
const error = ref('')
const busy = ref(false)
const fileInput = ref<HTMLInputElement>()

const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '')
const results = computed(() => {
  const term = norm(q.value)
  if (!term) return all.value.filter((i) => SUGGESTED.includes(i.s))
  const starts = all.value.filter((i) => norm(i.t).startsWith(term) || i.s.startsWith(term))
  const contains = all.value.filter((i) => !starts.includes(i) && norm(i.t).includes(term))
  return [...starts, ...contains].slice(0, 60)
})
const SUGGESTED = ['proxmox', 'homeassistant', 'docker', 'debian', 'ubuntu', 'paperlessngx', 'nginxproxymanager', 'nextcloud', 'synology', 'ubiquiti', 'jellyfin', 'plex', 'grafana', 'portainer', 'pihole', 'adguard', 'wireguard', 'truenas', 'vaultwarden', 'immich', 'gitea', 'raspberrypi', 'mariadb', 'postgresql']

onMounted(async () => {
  all.value = await iconIndex()
  uploads.value = await api<{ id: string; name: string }[]>('/api/v1/cockpit/icons')
})

async function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  error.value = ''
  busy.value = true
  try {
    const body = new FormData()
    body.append('file', file)
    const icon = await api<{ id: string; name: string }>('/api/v1/cockpit/icons', { method: 'POST', body })
    uploads.value.push(icon)
    emit('pick', { kind: 'upload', value: icon.id })
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busy.value = false
  }
}

async function removeUpload(id: string) {
  await api(`/api/v1/cockpit/icons/${id}`, { method: 'DELETE' })
  uploads.value = uploads.value.filter((u) => u.id !== id)
}
</script>

<template>
  <GlassDialog :title="$t('Choisir un logo')" wide @close="emit('close')">
    <div class="seg">
      <button type="button" :aria-pressed="tab === 'simple'" @click="tab = 'simple'">{{ $t('Bibliothèque') }}</button>
      <button type="button" :aria-pressed="tab === 'upload'" @click="tab = 'upload'">{{ $t('Mes logos') }}</button>
    </div>
    <template v-if="tab === 'simple'">
      <label class="search">
        <PhMagnifyingGlass :size="16" />
        <input v-model="q" class="input" :placeholder="$t('Proxmox, Home Assistant, Docker…')" :aria-label="$t('Rechercher un logo')" autofocus />
      </label>
      <p v-if="!q" class="faint hint">{{ $t('Suggestions — {n} logos disponibles (Simple Icons, CC0).', { n: all.length }) }}</p>
      <ul class="grid">
        <li v-for="i in results" :key="i.s">
          <button type="button" :title="i.t" @click="emit('pick', { kind: 'simple', value: i.s })">
            <TileIcon :icon="{ kind: 'simple', value: i.s }" :size="44" />
            <span>{{ i.t }}</span>
          </button>
        </li>
      </ul>
      <p v-if="q && !results.length" class="faint">{{ $t('Aucun logo trouvé. Importez le vôtre dans « Mes logos ».') }}</p>
    </template>
    <template v-else>
      <button class="btn" type="button" :disabled="busy" @click="fileInput?.click()"><PhUploadSimple :size="16" /> {{ busy ? $t('Import…') : $t('Importer un logo') }}</button>
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="onFile" />
      <p class="faint hint">{{ $t('PNG, JPEG ou WebP, 256 Ko maximum, de préférence carré et sur fond transparent.') }}</p>
      <p v-if="error" class="error-text">{{ error }}</p>
      <ul class="grid">
        <li v-for="u in uploads" :key="u.id" class="up">
          <button type="button" :title="u.name" @click="emit('pick', { kind: 'upload', value: u.id })">
            <TileIcon :icon="{ kind: 'upload', value: u.id }" :size="44" />
            <span>{{ u.name }}</span>
          </button>
          <button class="del" type="button" :aria-label="$t('Supprimer {name}', { name: u.name })" @click="removeUpload(u.id)"><PhTrash :size="13" /></button>
        </li>
      </ul>
    </template>
    <template #footer>
      <button class="btn" type="button" @click="emit('pick', null)">{{ $t('Logo automatique') }}</button>
      <button class="btn" type="button" @click="emit('close')">{{ $t('Annuler') }}</button>
    </template>
  </GlassDialog>
</template>

<style scoped>
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-2);
}
.hint {
  margin: 0;
  font-size: 12.5px;
}
.grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 8px;
  max-height: 46vh;
  overflow-y: auto;
}
.grid li {
  position: relative;
}
.grid button:first-child {
  width: 100%;
  display: grid;
  justify-items: center;
  gap: 6px;
  padding: 10px 4px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.4);
  font-size: 11.5px;
  font-weight: 560;
}
.grid button:first-child:hover {
  border-color: var(--accent);
}
.grid span {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.del {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: none;
  background: var(--surface-strong);
  display: grid;
  place-items: center;
  color: var(--down);
}
</style>
