/** Types de connexion : nom, logo (Simple Icons) et couleur de marque. `experimental` : pas encore validé sur du vrai matériel. */
import { tk } from '@/i18n'

export type ConnectorType = 'proxmox' | 'unifi' | 'synology' | 'docker'

export const CONNECTOR_TYPES: Record<ConnectorType, { label: string; icon: string; color: string; desc: string; experimental?: boolean }> = {
  proxmox: { label: 'Proxmox VE', icon: 'proxmox', color: '#e57000', desc: tk('Cluster, nœuds, VM et conteneurs LXC.') },
  unifi: { label: 'UniFi Network', icon: 'ubiquiti', color: '#1f6feb', desc: tk('Passerelle (UDM…), débit Internet, équipements et clients.') },
  synology: { label: 'Synology DSM', icon: 'synology', color: '#3c3c3c', desc: tk('NAS : disques, volumes, températures, sauvegardes.'), experimental: true },
  docker: { label: 'Docker', icon: 'docker', color: '#1d63ed', desc: tk('Conteneurs d\'un hôte Docker : état, santé, CPU et mémoire.'), experimental: true },
}

export const typeInfo = (t: string) => CONNECTOR_TYPES[t as ConnectorType] ?? { label: t, icon: '', color: '#888', desc: '' }
