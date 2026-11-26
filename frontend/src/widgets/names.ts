import { tk } from '@/i18n'

/** Noms des widgets de la Home (clés de traduction). */
export const WIDGET_NAMES = {
  search: tk('Recherche'),
  weather: tk('Météo'),
  calendar: tk('Agenda'),
  news: tk('News'),
  todo: tk('Tâches'),
  note: tk('Post-it'),
} as const

/** Libellés météo renvoyés par le serveur (codes WMO), déclarés ici pour la traduction. */
export const WEATHER_LABELS = [
  tk('Ciel dégagé'), tk('Plutôt dégagé'), tk('Éclaircies'), tk('Couvert'), tk('Brouillard'), tk('Brouillard givrant'),
  tk('Bruine légère'), tk('Bruine'), tk('Bruine dense'), tk('Bruine verglaçante'), tk('Pluie faible'), tk('Pluie'),
  tk('Pluie forte'), tk('Pluie verglaçante'), tk('Neige faible'), tk('Neige'), tk('Neige forte'), tk('Grains de neige'),
  tk('Averses'), tk('Averses violentes'), tk('Averses de neige'), tk('Orage'), tk('Orage avec grêle'), tk('Inconnu'),
]
