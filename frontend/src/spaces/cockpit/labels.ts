/**
 * Textes du Cockpit composés dans la langue de l'utilisateur à partir de données neutres
 * (type de tâche, type d'alerte + paramètres) renvoyées par le serveur.
 */
import type { AlertItem, PveTask } from '@/api/types'
import { t, tk } from '@/i18n'

const TASK_LABELS: Record<string, string> = {
  vzdump: tk('Sauvegarde'),
  qmstart: tk('Démarrage VM'),
  qmstop: tk('Arrêt VM'),
  qmshutdown: tk('Extinction VM'),
  qmreboot: tk('Redémarrage VM'),
  vzstart: tk('Démarrage LXC'),
  vzstop: tk('Arrêt LXC'),
  vzshutdown: tk('Extinction LXC'),
  vzreboot: tk('Redémarrage LXC'),
  qmigrate: tk('Migration VM'),
  vzmigrate: tk('Migration LXC'),
  qmclone: tk('Clonage VM'),
  vzcreate: tk('Création LXC'),
  qmcreate: tk('Création VM'),
  aptupdate: tk('Mise à jour des paquets'),
  startall: tk('Démarrage des invités'),
  stopall: tk('Arrêt des invités'),
  imgcopy: tk("Copie d'image"),
  download: tk('Téléchargement'),
}

export function taskLabel(type: string, fallback?: string): string {
  const key = TASK_LABELS[type]
  return key ? t(key) : (fallback ?? type)
}

// Accord du participe en français (« Sauvegarde terminée », « Démarrage terminé »)
const FEMININE = new Set(['vzdump', 'qmshutdown', 'vzshutdown', 'qmigrate', 'vzmigrate', 'vzcreate', 'qmcreate', 'aptupdate', 'imgcopy'])

export function taskPhrase(task: PveTask): string {
  const f = FEMININE.has(task.type)
  const result = {
    ok: f ? t('terminée') : t('terminé'),
    warning: f ? t('terminée avec avertissements') : t('terminé avec avertissements'),
    error: t('en échec'),
    running: t('en cours'),
  }[task.state]
  const label = taskLabel(task.type, task.label)
  const who = task.target_name || (task.target ? `#${task.target}` : '')
  return who ? t('{label} de {who} {result}', { label, who, result }) : t('{label} sur {node} {result}', { label, node: task.node, result })
}

type P = Record<string, string | number | null | undefined>

export function alertTitle(a: AlertItem): string {
  const p = (a.params ?? {}) as P
  if (!Object.keys(p).length) return a.title // alerte antérieure à la traduction
  switch (a.kind) {
    case 'quorum':
      return t('Quorum perdu sur le cluster {cluster}', p)
    case 'node-offline':
      return t('Nœud {node} hors ligne', p)
    case 'cpu':
      return t('CPU élevé sur {node}', p)
    case 'memory':
      return t('Mémoire presque pleine sur {node}', p)
    case 'storage':
      return p.node ? t('Stockage {storage} (sur {node}) presque plein', p) : t('Stockage {storage} (partagé) presque plein', p)
    case 'guest-stopped':
      return p.type === 'qemu' ? t('VM {name} ({vmid}) arrêtée', p) : t('LXC {name} ({vmid}) arrêté', p)
    case 'backup':
      return t('Sauvegarde de {name} en échec', p)
    case 'task':
      return t('{label} en échec ({who})', { label: taskLabel(String(p.task)), who: p.who })
    case 'connector':
      return t('{name} injoignable', p)
    case 'device-offline':
      return t('{name} hors ligne', p)
    case 'nas-hardware':
      return t('NAS : anomalie {part}', { part: t(NAS_PARTS[String(p.part)] ?? String(p.part)) })
    case 'disk':
      return t('Disque {name} : {state}', { name: p.name, state: t(DISK_STATES[String(p.state)] ?? String(p.state)) })
    case 'volume':
      return t('{name} : {state}', { name: p.name, state: t(DISK_STATES[String(p.state)] ?? String(p.state)) })
    case 'volume-full':
      return t('{name} presque plein', p)
    case 'container-stopped':
      return t('Conteneur {name} arrêté', p)
    case 'container-unhealthy':
      return t('Conteneur {name} en mauvaise santé', p)
    case 'container-restarting':
      return t('Conteneur {name} redémarre en boucle', p)
    default:
      return a.title
  }
}

const NAS_PARTS: Record<string, string> = {
  system: tk('système'),
  power: tk('alimentation'),
  fans: tk('ventilateurs'),
  thermal: tk('température'),
}
const DISK_STATES: Record<string, string> = {
  warning: tk('avertissement'),
  critical: tk('critique'),
  failing: tk('défaillant'),
  crashed: tk('en panne'),
  partition_failed: tk('partition système endommagée'),
  disconnected: tk('déconnecté'),
  degraded: tk('dégradé'),
}

export function alertDetail(a: AlertItem): string | null {
  const p = (a.params ?? {}) as P
  if (!Object.keys(p).length) return a.detail
  switch (a.kind) {
    case 'quorum':
      return t('Le cluster ne peut plus prendre de décision : vérifiez les nœuds et le réseau.')
    case 'cpu':
      return t('Au moins {pct} % depuis {minutes} minutes', { minutes: 5, ...p })
    case 'memory':
    case 'storage':
    case 'volume-full':
      return `${p.pct} %`
    case 'container-stopped':
      return p.code != null ? t('Code de sortie {code}', p) : a.detail
    case 'guest-stopped':
      return t('Sur {node}', p)
    default:
      return a.detail // message technique (statut de tâche, erreur réseau)
  }
}
