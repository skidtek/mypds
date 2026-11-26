import { onBeforeUnmount, onMounted } from 'vue'

/**
 * Rafraîchit une donnée à intervalle régulier, uniquement quand l'onglet est visible,
 * et immédiatement au retour sur l'onglet si la donnée est périmée.
 */
export function usePolling(fn: () => Promise<void> | void, intervalMs: number) {
  let timer: number | undefined
  let last = 0
  const run = async () => {
    last = Date.now()
    try {
      await fn()
    } catch {
      /* l'erreur est affichée par le widget */
    }
  }
  const onVisible = () => {
    if (document.visibilityState === 'visible' && Date.now() - last > intervalMs) void run()
  }
  onMounted(() => {
    void run()
    timer = window.setInterval(() => document.visibilityState === 'visible' && void run(), intervalMs)
    document.addEventListener('visibilitychange', onVisible)
  })
  onBeforeUnmount(() => {
    window.clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisible)
  })
  return { refresh: run }
}
