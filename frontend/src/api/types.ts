export interface Me {
  username: string
  display_name: string
  role: 'viewer' | 'operator' | 'admin'
  csrf_token: string
  avatar_version: string | null
}

export type BackgroundName = 'nature' | 'abstract' | 'minimal' | 'it' | 'custom'
export type SearchEngine = 'google' | 'bing' | 'duckduckgo' | 'qwant' | 'custom'

export interface Preferences {
  background: BackgroundName
  color_mode: 'auto' | 'light' | 'dark'
  accent: string
  blur: number
  transparency: number
  search_engine: SearchEngine
  search_custom_url: string | null
  search_autofocus: boolean
  temperature_unit: 'celsius' | 'fahrenheit'
  wallpaper_light: string | null
  wallpaper_dark: string | null
  locale: 'auto' | 'fr' | 'en'
}

export interface Branding {
  title: string
  short_title: string
  subtitle: string
  display: 'full' | 'short' | 'hidden'
  show_logo: boolean
  logo_position: 'top' | 'left' | 'right'
  logo_version: string | null
}

export type WidgetType = 'search' | 'weather' | 'calendar' | 'news' | 'todo' | 'note'

export interface Placement {
  x: number
  y: number
  w: number
  h: number
}

export interface Widget {
  id: string
  type: WidgetType
  title: string | null
  hidden: boolean
  config: Record<string, unknown>
  placement: { desktop: Placement | null; tablet: Placement | null; mobile_h: number | null }
}

export interface LandingDocument {
  schema: 'mypds.landing-layout'
  version: 1
  widgets: Widget[]
  mobile: { mode: 'auto' | 'custom'; order: string[] }
}

export interface LayoutResponse {
  revision: number
  document: LandingDocument
}

export type Condition =
  | 'clear'
  | 'partly-cloudy'
  | 'cloudy'
  | 'fog'
  | 'drizzle'
  | 'rain'
  | 'snow'
  | 'showers'
  | 'thunderstorm'
  | 'unknown'

export interface WeatherReport {
  provider: string
  attribution: string
  timezone: string
  utc_offset_seconds: number
  unit: 'celsius' | 'fahrenheit'
  fetched_at: string
  current: {
    temperature: number
    apparent_temperature: number | null
    condition: Condition
    label: string
    is_day: boolean
    humidity: number | null
    wind_speed: number | null
    wind_gusts: number | null
    wind_direction: number | null
    precipitation: number | null
  }
  days: {
    date: string
    condition: Condition
    label: string
    temp_min: number
    temp_max: number
    sunrise: string | null
    sunset: string | null
    precipitation_sum: number | null
    precipitation_probability: number | null
    uv_index_max: number | null
    wind_max: number | null
  }[]
  /** Échelle européenne en Europe, américaine ailleurs ; niveau 0 (bon) à 5 commun aux deux. */
  air: { scale: 'eu' | 'us'; index: number; level: number } | null
}

export interface Place {
  name: string
  admin: string | null
  country: string | null
  latitude: number
  longitude: number
  timezone: string | null
}

export interface CalendarSource {
  id: string
  name: string
  color: string
  enabled: boolean
  url_host: string
  auth_username: string | null
  event_count: number
  last_success_at: string | null
  last_error: string | null
}

export interface CalendarEvent {
  id: string
  source_id: string
  title: string
  start: string
  end: string | null
  all_day: boolean
  location: string | null
  color: string
}

export interface RssCategory {
  id: string
  name: string
  position: number
  feed_count: number
}

export interface RssFeed {
  id: string
  title: string
  feed_url: string
  site_url: string | null
  category_id: string | null
  enabled: boolean
  last_success_at: string | null
  last_error: string | null
}

export interface RssItem {
  id: string
  title: string
  link: string | null
  source: string
  feed_id: string
  category_id: string | null
  published_at: string
  summary: string | null
  image: string | null
}

// ---------------- Cockpit ----------------
export interface IconRef {
  kind: 'simple' | 'upload'
  value: string
}

export type TileType =
  | 'proxmox.summary'
  | 'proxmox.node'
  | 'proxmox.guest'
  | 'unifi.summary'
  | 'unifi.device'
  | 'synology.summary'
  | 'docker.summary'
  | 'docker.container'
  | 'link'
  | 'alerts'
  | 'activity'

export interface CockpitTile {
  id: string
  type: TileType
  width: { desktop: number }
  config: {
    connector_id?: string
    node?: string
    guest?: string
    device?: string
    container?: string
    label?: string
    url?: string
    icon?: IconRef
  }
}

export interface CockpitRow {
  id: string
  title?: string | null
  tiles: CockpitTile[]
}

export interface CockpitGroup {
  id: string
  title: string
  icon?: string | null
  rows: CockpitRow[]
}

export interface CockpitDocument {
  schema: 'mypds.cockpit-layout'
  version: 1
  groups: CockpitGroup[]
  known_connectors?: string[]
}

export interface PveNode {
  name: string
  online: boolean
  ip: string | null
  cpu: number | null
  maxcpu: number | null
  mem: number | null
  maxmem: number | null
  disk: number | null
  maxdisk: number | null
  uptime: number | null
  vms: number
  lxcs: number
}

export interface PveGuest {
  id: string
  vmid: number
  type: 'qemu' | 'lxc'
  name: string
  node: string
  status: string
  cpu: number | null
  maxcpu: number | null
  mem: number | null
  maxmem: number | null
  uptime: number | null
  tags: string[]
  on_demand?: boolean
}

export interface PveTask {
  upid: string
  type: string
  label: string
  target: string
  target_name: string
  node: string
  user: string
  start: number
  end: number | null
  state: 'running' | 'ok' | 'warning' | 'error'
  status: string | null
}

export interface PveSummary {
  cluster: { name: string | null; standalone: boolean; quorate: boolean | null; nodes_online: number; nodes_total: number; health: 'ok' | 'warning' | 'down' | 'unknown' }
  guests: { vm_running: number; vm_stopped: number; lxc_running: number; lxc_stopped: number }
  resources: { cpu: number | null; cpus: number; mem_used: number; mem_total: number; mem: number | null; disk_used: number; disk_total: number; disk: number | null }
  nodes: PveNode[]
  guest_list: PveGuest[]
  tasks?: PveTask[]
}

export interface ConnectorSnapshot {
  id: string
  name: string
  type: string
  demo: boolean
  status: string
  fetched_at: string | null
  error: string | null
  data: PveSummary | null
}

export interface ConnectorInstance {
  id: string
  type: string
  name: string
  enabled: boolean
  config: Record<string, unknown>
  secrets_set: string[]
  poll_interval_s: number
  status: string
  last_ok_at: string | null
  last_error: string | null
  demo: boolean
}

export interface HistoryPoint {
  t: number
  cpu: number | null
  mem: number | null
  netin: number | null
  netout: number | null
}

export interface AlertItem {
  id: string
  connector_id: string
  connector: string
  demo: boolean
  kind: string
  resource: string | null
  severity: 'critical' | 'warning'
  title: string
  detail: string | null
  params?: Record<string, string | number | null>
  state: 'firing' | 'resolved'
  started_at: string
  resolved_at: string | null
}

export interface UserSession {
  id: string
  current: boolean
  trusted: boolean
  created_at: string
  last_seen_at: string
  expires_at: string
  ip: string | null
  user_agent: string | null
}

export interface TodoItem {
  id: string
  text: string
  position: number
  created_at: string
  done_at: string | null
}

export type NoteColor = 'yellow' | 'pink' | 'green' | 'blue' | 'orange' | 'purple'
export type NoteTexture = 'plain' | 'paper' | 'lined' | 'grid'
export interface NoteItem {
  id: string
  title: string
  body: string
  color: NoteColor
  texture: NoteTexture
  position: number
  created_at: string
  updated_at: string
}

// ---------- UniFi ----------
export interface UnifiDevice {
  id: string
  name: string
  model: string | null
  kind: 'gateway' | 'switch' | 'ap' | 'other'
  state: string
  online: boolean
  ip: string | null
  firmware: string | null
  firmware_updatable: boolean
  uptime_s: number | null
  cpu_pct: number | null
  mem_pct: number | null
  tx_bps: number | null
  rx_bps: number | null
}
export interface UnifiData {
  site: { id: string; name: string }
  app_version: string | null
  gateway: UnifiDevice | null
  wan: { down_bps: number | null; up_bps: number | null } | null
  devices: UnifiDevice[]
  counts: { devices: number; online: number; offline: number; updates: number }
  clients: { total: number; wired: number; wireless: number; vpn: number }
  unavailable: string[]
}

// ---------- Synology ----------
export interface SynologyDisk {
  id: string
  name: string
  model: string | null
  status: string
  health: string | null
  temperature: number | null
  remain_life: number | null
}
export interface SynologyVolume {
  id: string
  name: string
  state: 'normal' | 'degraded' | 'crashed' | 'busy' | 'unknown'
  total: number
  used: number
  pct: number | null
}
export interface SynologyData {
  model: string | null
  version: string | null
  system_ok: boolean | null
  power_ok: boolean | null
  fans_ok: boolean | null
  thermal_ok: boolean | null
  temperature: number | null
  cpu_pct: number | null
  mem_pct: number | null
  update_available: boolean | null
  disks: SynologyDisk[]
  volumes: SynologyVolume[]
  backups:
    | { available: true; tasks: { name: string; state: string | null; last_result: string | null; ok: boolean | null; last_time: string | null; next_time: string | null }[] }
    | { available: false; reason: string }
    | null
  url: string | null
}

// ---------- Docker ----------
export interface DockerContainer {
  id: string
  name: string
  image: string | null
  state: string
  status: string | null
  health: string | null
  restart_count: number | null
  exit_code: number | null
  project: string | null
  ports: string[]
  cpu_pct: number | null
  mem_used: number | null
  mem_limit: number | null
  on_demand: boolean
}
export interface DockerData {
  host: { name: string | null; docker_version: string | null; os: string | null; cpus: number | null; mem_total: number | null; images: number | null }
  counts: { total: number; running: number; stopped: number; unhealthy: number; restarting: number }
  containers: DockerContainer[]
}
