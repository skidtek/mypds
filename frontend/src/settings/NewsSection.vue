<script setup lang="ts">
import { serverText } from '@/i18n/server'
import { PhArrowClockwise, PhDownloadSimple, PhFolderPlus, PhTrash, PhUploadSimple, PhWarningCircle } from '@phosphor-icons/vue'
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import type { RssCategory, RssFeed } from '@/api/types'
import { since } from '@/design-system/time'
import { t } from '@/i18n'

const feeds = ref<RssFeed[]>([])
const categories = ref<RssCategory[]>([])
const url = ref('')
const category = ref<string>('')
const newCat = ref('')
const busy = ref(false)
const error = ref('')
const report = ref('')
const confirmId = ref<string | null>(null)
const fileInput = ref<HTMLInputElement>()

async function load() {
  ;[feeds.value, categories.value] = await Promise.all([
    api<RssFeed[]>('/api/v1/rss/feeds'),
    api<RssCategory[]>('/api/v1/rss/categories'),
  ])
}
onMounted(load)

const grouped = computed(() => {
  const groups = categories.value.map((c) => ({ id: c.id, name: c.name, feeds: feeds.value.filter((f) => f.category_id === c.id) }))
  const none = feeds.value.filter((f) => !f.category_id)
  if (none.length) groups.push({ id: '', name: 'Sans catégorie', feeds: none })
  return groups
})

async function add() {
  busy.value = true
  error.value = ''
  try {
    await api('/api/v1/rss/feeds', { method: 'POST', json: { url: url.value, category_id: category.value || null } })
    url.value = ''
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

async function addCategory() {
  if (!newCat.value.trim()) return
  await api('/api/v1/rss/categories', { method: 'POST', json: { name: newCat.value.trim(), position: categories.value.length } })
  newCat.value = ''
  await load()
}

async function removeCategory(id: string) {
  if (confirmId.value !== id) {
    confirmId.value = id
    return
  }
  await api(`/api/v1/rss/categories/${id}`, { method: 'DELETE' })
  confirmId.value = null
  await load()
}

async function patch(f: RssFeed, body: Partial<RssFeed>) {
  Object.assign(f, await api<RssFeed>(`/api/v1/rss/feeds/${f.id}`, { method: 'PATCH', json: body }))
}
async function refresh(f: RssFeed) {
  Object.assign(f, await api<RssFeed>(`/api/v1/rss/feeds/${f.id}/refresh`, { method: 'POST' }))
}
async function remove(f: RssFeed) {
  if (confirmId.value !== f.id) {
    confirmId.value = f.id
    return
  }
  await api(`/api/v1/rss/feeds/${f.id}`, { method: 'DELETE' })
  confirmId.value = null
  await load()
}

async function importOpml(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  error.value = report.value = ''
  busy.value = true
  try {
    const body = new FormData()
    body.append('file', file)
    const r = await api<{ feeds_added: number; feeds_skipped: number; categories_added: number }>('/api/v1/rss/opml', { method: 'POST', body })
    report.value = t('{added} flux importés, {cats} catégories créées, {skipped} déjà présents. Les articles arrivent dans quelques instants.', {
      added: r.feeds_added,
      cats: r.categories_added,
      skipped: r.feeds_skipped,
    })
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busy.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}
</script>

<template>
  <section class="sec">
    <h2>{{ $t('Actualités') }}</h2>
    <p class="muted">{{ $t('Les flux sont récupérés par le serveur toutes les 30 minutes. Vous pouvez importer vos abonnements NetNewsWire (Fichier → Exporter les abonnements… → OPML).') }}</p>
    <div class="actions">
      <button class="btn" type="button" :disabled="busy" @click="fileInput?.click()"><PhUploadSimple :size="16" /> {{ $t('Importer un OPML') }}</button>
      <input ref="fileInput" type="file" accept=".opml,.xml,text/xml,text/x-opml" hidden @change="importOpml" />
      <a class="btn" href="/api/v1/rss/opml" download><PhDownloadSimple :size="16" /> {{ $t('Exporter en OPML') }}</a>
    </div>
    <p v-if="report" class="ok-text">{{ report }}</p>

    <form class="add" @submit.prevent="add">
      <label class="field grow"><span>{{ $t('Ajouter un flux RSS / Atom ou un site') }}</span><input v-model="url" class="input" required inputmode="url" :placeholder="$t('https://exemple.org ou https://exemple.org/feed.xml')" /></label>
      <label class="field">
        <span>{{ $t('Catégorie') }}</span>
        <select v-model="category" class="input">
          <option value="">{{ $t('Sans catégorie') }}</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </label>
      <button class="btn primary" type="submit" :disabled="busy">{{ busy ? $t('Vérification…') : $t('Ajouter') }}</button>
    </form>
    <p v-if="error" class="error-text">{{ error }}</p>

    <form class="add" @submit.prevent="addCategory">
      <label class="field grow"><span>{{ $t('Nouvelle catégorie') }}</span><input v-model="newCat" class="input" maxlength="80" :placeholder="$t('Tech, Homelab, Actualités…')" /></label>
      <button class="btn" type="submit"><PhFolderPlus :size="16" /> {{ $t('Créer') }}</button>
    </form>

    <div v-for="g in grouped" :key="g.id || 'none'" class="group">
      <h3>
        {{ g.name }} <span class="faint">({{ g.feeds.length }})</span>
        <button v-if="g.id" class="icon-btn" :class="{ danger: confirmId === g.id }" type="button" :aria-label="confirmId === g.id ? $t('Confirmer : supprimer la catégorie (les flux sont conservés)') : $t('Supprimer la catégorie {name}', { name: g.name })" @click="removeCategory(g.id)" @blur="confirmId = null">
          <PhTrash :size="15" />
        </button>
      </h3>
      <ul class="list">
        <li v-for="f in g.feeds" :key="f.id">
          <div class="info">
            <strong>{{ f.title }}</strong>
            <span class="faint url">{{ f.feed_url }}</span>
            <span v-if="f.last_error" class="error-text"><PhWarningCircle :size="13" /> {{ serverText(f.last_error) }}</span>
            <span v-else-if="f.last_success_at" class="faint">{{ $t('Mis à jour {when}', { when: since(f.last_success_at) }) }}</span>
          </div>
          <select class="input cat" :value="f.category_id ?? ''" :aria-label="$t('Catégorie de {name}', { name: f.title })" @change="patch(f, { category_id: ($event.target as HTMLSelectElement).value || null })">
            <option value="">{{ $t('Sans catégorie') }}</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <label class="check"><input type="checkbox" :checked="f.enabled" :aria-label="$t('Activer {name}', { name: f.title })" @change="patch(f, { enabled: ($event.target as HTMLInputElement).checked })" /></label>
          <button class="icon-btn" type="button" :aria-label="$t('Actualiser {name}', { name: f.title })" @click="refresh(f)"><PhArrowClockwise :size="17" /></button>
          <button class="icon-btn" :class="{ danger: confirmId === f.id }" type="button" :aria-label="confirmId === f.id ? $t('Confirmer la suppression') : $t('Supprimer {name}', { name: f.title })" @click="remove(f)" @blur="confirmId = null">
            <PhTrash :size="17" />
          </button>
        </li>
      </ul>
    </div>
    <p v-if="!feeds.length" class="faint">{{ $t('Aucun flux pour l\'instant.') }}</p>
  </section>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.add {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.grow {
  flex: 1;
  min-width: 220px;
}
.group h3 {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  margin: 8px 0;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}
.list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: rgb(var(--surface-rgb) / 0.5);
}
.info {
  flex: 1;
  display: grid;
  gap: 2px;
  min-width: 0;
  font-size: 12.5px;
}
.info strong {
  font-size: 14px;
}
.url {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cat {
  width: auto;
  max-width: 160px;
  padding: 6px 10px;
  font-size: 13px;
}
.icon-btn.danger {
  color: #fff;
  background: var(--down);
}
.ok-text {
  color: var(--ok);
  font-weight: 560;
}
p {
  margin: 0;
}
@media (max-width: 699px) {
  .cat {
    display: none;
  }
}
</style>
