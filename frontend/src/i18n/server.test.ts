import { afterEach, describe, expect, it } from 'vitest'
import { locale } from './index'
import { serverText } from './server'

describe('serverText', () => {
  afterEach(() => {
    locale.value = 'fr'
  })

  it('laisse les messages intacts en français', () => {
    locale.value = 'fr'
    expect(serverText('Tâche introuvable')).toBe('Tâche introuvable')
  })

  it('traduit les messages exacts et les gabarits, y compris imbriqués', () => {
    locale.value = 'en'
    expect(serverText('Tâche introuvable')).toBe('Task not found')
    expect(serverText('Réponse inattendue de Proxmox (HTTP 500)')).toBe('Unexpected response from Proxmox (HTTP 500)')
    expect(serverText('Configuration invalide : Port SNMP : valeur invalide')).toBe('Invalid configuration: SNMP port: invalid value')
    expect(serverText('Connexion impossible : All connection attempts failed ([Errno 65] No route to host)')).toBe(
      "Can't connect: All connection attempts failed ([Errno 65] No route to host)",
    )
  })

  it('traduit chaque partie d\'une erreur de validation composée', () => {
    locale.value = 'en'
    expect(serverText('Adresse : valeur invalide ; Site : valeur invalide')).toBe('Address: invalid value; Site: invalid value')
  })

  it('rend tel quel un message inconnu', () => {
    locale.value = 'en'
    expect(serverText('Something else entirely')).toBe('Something else entirely')
    expect(serverText(null)).toBe('')
  })
})
