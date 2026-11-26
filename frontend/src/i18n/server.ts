/**
 * Messages renvoyés par le serveur (erreurs d'API, état des connexions, des flux et des agendas).
 * Le serveur écrit en français ; ce catalogue les traduit pour l'interface anglaise.
 * Clé = gabarit français, `{}` marquant une partie variable (elle-même traduite si elle est connue).
 * Vérifié par backend/tests/test_server_messages.py : chaque message du serveur doit figurer ici.
 */
import { locale } from './index'

export const SERVER_EN: Record<string, string> = {
  // Connexions : champs (messages de validation composés)
  "Adresse": "Address",
  "Port": "Port",
  "Port SNMP": "SNMP port",
  "Port DSM": "DSM port",
  "Identifiant du jeton": "Token ID",
  "Site": "Site",
  "Utilisateur SNMP": "SNMP user",
  "Empreinte": "Fingerprint",
  "Lien": "Link",
  "Adresse invalide : indiquez seulement l'IP ou le nom (ex. 192.168.0.1)": "Invalid address: enter only the IP or host name (e.g. 192.168.0.1)",
  "{} : trop court ({} caractères minimum)": "{}: too short ({} characters minimum)",
  "{} : valeur invalide": "{}: invalid value",

  // Comptes et sessions
  "Authentification requise": "Sign-in required",
  "Identifiant ou mot de passe incorrect": "Incorrect username or password",
  "Trop de tentatives. Réessayez dans quelques minutes.": "Too many attempts. Try again in a few minutes.",
  "Session expirée": "Session expired",
  "Session introuvable": "Session not found",
  "Identifiant de session invalide": "Invalid session ID",
  "Utilisez « Se déconnecter » pour fermer la session actuelle": "Use “Sign out” to close the current session",
  "Jeton CSRF invalide": "Invalid CSRF token",
  "Origine refusée": "Origin refused",
  "Requête inter-sites refusée": "Cross-site request refused",
  "Permission insuffisante": "Insufficient permission",
  "Mot de passe actuel incorrect": "Current password is incorrect",
  "Le nouveau mot de passe doit être différent de l'actuel": "The new password must be different from the current one",
  "Le mot de passe doit contenir au moins {} caractères": "The password must be at least {} characters long",
  "Aucune photo": "No photo",
  "Photo trop volumineuse (5 Mo maximum)": "Photo too large (5 MB maximum)",

  // Apparence, marque, images
  "Aucun fond d'écran importé": "No wallpaper uploaded",
  "Aucun logo importé": "No logo uploaded",
  "Format non pris en charge : utilisez une image PNG, JPEG ou WebP": "Unsupported format: use a PNG, JPEG or WebP image",
  "Image trop volumineuse (8 Mo maximum)": "Image too large (8 MB maximum)",
  "Logo trop volumineux (256 Ko maximum)": "Logo too large (256 KB maximum)",
  "Logo trop volumineux (512 Ko maximum)": "Logo too large (512 KB maximum)",
  "Logo introuvable": "Logo not found",
  "L'URL doit commencer par http(s):// et contenir %s à la place des mots-clés": "The URL must start with http(s):// and contain %s where the search terms go",

  // Dispositions
  "Disposition invalide : {}": "Invalid layout: {}",
  "Disposition trop volumineuse": "Layout too large",
  "La disposition a été modifiée ailleurs. Rechargez la page.": "The layout was changed elsewhere. Reload the page.",
  "Identifiants de widgets en double": "Duplicate widget IDs",
  "Identifiants en double dans la disposition": "Duplicate IDs in the layout",
  "Le widget dépasse la grille {} ({} colonnes)": "The widget goes beyond the {} grid ({} columns)",
  "Version de disposition non prise en charge : {}": "Unsupported layout version: {}",
  "Trop de tuiles (500 maximum)": "Too many tiles (500 maximum)",
  "L'adresse doit commencer par http:// ou https://": "The address must start with http:// or https://",

  // Tâches et post-it
  "Tâche introuvable": "Task not found",
  "Liste pleine ({} tâches maximum) : supprimez des tâches terminées": "List full ({} tasks maximum): delete some completed tasks",
  "Note introuvable": "Note not found",
  "{} post-it maximum par widget": "{} sticky notes maximum per widget",

  // Météo
  "Météo indisponible : {}": "Weather unavailable: {}",
  "Recherche de lieu indisponible : {}": "Place search unavailable: {}",
  "Service météo indisponible (HTTP {})": "Weather service unavailable (HTTP {})",

  // Actualités
  "Catégorie introuvable": "Category not found",
  "Flux introuvable": "Feed not found",
  "Ce flux est déjà dans vos abonnements": "You're already subscribed to this feed",
  "Impossible d'ajouter ce flux : {}": "Can't add this feed: {}",
  "Ce document n'est pas un flux RSS ou Atom valide": "This document isn't a valid RSS or Atom feed",
  "Ni flux RSS/Atom, ni page annonçant un flux à cette adresse": "No RSS/Atom feed, and no page announcing one, at this address",
  "La page annonce un flux, mais il est illisible : {}": "The page announces a feed, but it can't be read: {}",
  "Flux refusé : déclaration d'entités XML": "Feed refused: XML entity declaration",
  "Fichier OPML invalide": "Invalid OPML file",
  "Fichier OPML sans élément <body>": "OPML file without a <body> element",
  "Fichier OPML trop volumineux (2 Mo max)": "OPML file too large (2 MB max)",
  "Image introuvable": "Image not found",
  "Image indisponible": "Image unavailable",

  // Agendas
  "Calendrier introuvable": "Calendar not found",
  "Calendrier inaccessible : {}": "Calendar unreachable: {}",
  "Fichier ICS invalide": "Invalid ICS file",
  "Mot de passe requis pour l'identifiant indiqué": "A password is required for this username",
  "Le serveur a répondu HTTP {}": "The server answered HTTP {}",
  "HTTP {}": "HTTP {}",

  // Réseau sortant
  "URL invalide": "Invalid URL",
  "URL sans nom d'hôte": "URL without a host name",
  "Seuls les schémas http et https sont acceptés": "Only http and https are accepted",
  "Les identifiants dans l'URL ne sont pas acceptés": "Credentials in the URL aren't accepted",
  "Identifiants refusés sur une connexion non chiffrée : utilisez https://": "Credentials refused over an unencrypted connection: use https://",
  "Nom d'hôte introuvable : {}": "Host name not found: {}",
  "Adresse non autorisée pour {} ({}). Un administrateur peut l'ajouter à MYPDS_OUTBOUND_ALLOW_HOSTS.": "Address not allowed for {} ({}). An admin can add it to MYPDS_OUTBOUND_ALLOW_HOSTS.",
  "Connexion impossible : {}": "Can't connect: {}",
  "Délai dépassé": "Timed out",
  "Trop de redirections": "Too many redirects",
  "Réponse trop volumineuse (> {} Ko)": "Response too large (> {} KB)",
  "Empreinte TLS invalide : SHA-256 attendue (64 caractères hexadécimaux)": "Invalid TLS fingerprint: a SHA-256 is expected (64 hexadecimal characters)",
  "Empreinte du certificat TLS inattendue : connexion refusée": "Unexpected TLS certificate fingerprint: connection refused",
  "Certificat d'autorité (CA) illisible : collez le contenu PEM de ca.pem": "Unreadable CA certificate: paste the PEM content of ca.pem",
  "Certificat ou clé client illisible : collez le contenu PEM de cert.pem et key.pem": "Unreadable client certificate or key: paste the PEM content of cert.pem and key.pem",

  // Chiffrement
  "Clé de chiffrement illisible : {}": "Unreadable encryption key: {}",
  "La clé {} doit faire exactement 32 octets": "The key {} must be exactly 32 bytes",
  "Identifiant de clé inconnu": "Unknown key ID",

  // Connexions : général
  "Connecteur introuvable": "Connection not found",
  "Type de connecteur inconnu : {}": "Unknown connector type: {}",
  "Configuration invalide : {}": "Invalid configuration: {}",
  "Historique non disponible pour ce connecteur": "History isn't available for this connector",
  "Option réservée aux connexions Proxmox et Docker": "Only available for Proxmox and Docker connections",
  "Élément invalide pour ce type de connexion": "Invalid item for this type of connection",
  "Seuils invalides : {}": "Invalid thresholds: {}",
  "Le seuil d'avertissement doit être inférieur ou égal au seuil critique": "The warning threshold must be lower than or equal to the critical threshold",
  "Le lien doit commencer par https:// ou http://": "The link must start with https:// or http://",

  // Proxmox
  "Hôte et identifiant de jeton requis (ou choisissez le mode démo)": "Host and token ID required (or choose demo mode)",
  "Secret du jeton API manquant": "API token secret missing",
  "Jeton refusé (HTTP 401) : vérifiez l'identifiant et le secret": "Token refused (HTTP 401): check the ID and the secret",
  "Droits insuffisants (HTTP 403) : le jeton doit avoir le rôle PVEAuditor sur /": "Insufficient rights (HTTP 403): the token needs the PVEAuditor role on /",
  "Réponse inattendue de Proxmox (HTTP {})": "Unexpected response from Proxmox (HTTP {})",
  "Réponse Proxmox illisible": "Unreadable Proxmox response",
  "Invité invalide : {}": "Invalid guest: {}",
  "Période inconnue": "Unknown period",
  "Ressource invalide": "Invalid resource",

  // UniFi
  "Adresse de la console UniFi requise (ou choisissez le mode démo)": "UniFi console address required (or choose demo mode)",
  "Clé API UniFi manquante": "UniFi API key missing",
  "Clé API refusée (HTTP 401) : vérifiez la clé d'intégration": "API key refused (HTTP 401): check the integration key",
  "Accès refusé (HTTP 403) : la clé doit venir d'un compte administrateur": "Access denied (HTTP 403): the key must come from an administrator account",
  "API d'intégration introuvable (HTTP 404) : mettez à jour l'application UniFi Network (9.0 ou plus)": "Integration API not found (HTTP 404): update the UniFi Network application (9.0 or later)",
  "Réponse inattendue de la console UniFi (HTTP {})": "Unexpected response from the UniFi console (HTTP {})",
  "Réponse UniFi illisible": "Unreadable UniFi response",
  "Aucun site UniFi trouvé": "No UniFi site found",
  "Site « {} » introuvable": "Site “{}” not found",

  // Synology
  "Adresse du NAS et utilisateur SNMP v3 requis (ou choisissez le mode démo)": "NAS address and SNMP v3 user required (or choose demo mode)",
  "Compte DSM requis pour l'API DSM": "A DSM account is required for the DSM API",
  "Mots de passe SNMP v3 (authentification et chiffrement) manquants": "SNMP v3 passwords (authentication and privacy) missing",
  "Pas de réponse SNMP : vérifiez l'adresse, le port 161/UDP et que SNMP v3 est activé": "No SNMP response: check the address, UDP port 161 and that SNMP v3 is enabled",
  "Adresse SNMP injoignable : {}": "SNMP address unreachable: {}",
  "Identifiants SNMP v3 refusés : {}": "SNMP v3 credentials refused: {}",
  "Erreur SNMP : {}": "SNMP error: {}",
  "Le NAS répond mais ne fournit pas la MIB Synology : SNMP est-il activé dans DSM ?": "The NAS answers but doesn't provide the Synology MIB: is SNMP enabled in DSM?",
  "API DSM : HTTP {}": "DSM API: HTTP {}",

  // Docker
  "Adresse de l'hôte Docker requise (ou choisissez le mode démo)": "Docker host address required (or choose demo mode)",
  "Certificats TLS manquants (ca.pem, cert.pem, key.pem)": "TLS certificates missing (ca.pem, cert.pem, key.pem)",
  "Accès refusé par Docker (HTTP {}) : certificat client non reconnu": "Access denied by Docker (HTTP {}): client certificate not recognized",
  "Réponse inattendue de Docker (HTTP {})": "Unexpected response from Docker (HTTP {})",
  "Réponse Docker illisible": "Unreadable Docker response",
  "Liste des conteneurs illisible": "Unreadable container list",
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const TEMPLATES = Object.entries(SERVER_EN)
  .filter(([fr]) => fr.includes('{}'))
  .map(([fr, en]) => ({ re: new RegExp(`^${fr.split('{}').map(escape).join('(.+?)')}$`, 's'), en }))
  // Gabarits les plus précis d'abord (« HTTP {} » en dernier)
  .sort((a, b) => b.re.source.length - a.re.source.length)

function translateOne(msg: string): string {
  const exact = SERVER_EN[msg]
  if (exact !== undefined) return exact
  for (const { re, en } of TEMPLATES) {
    const m = re.exec(msg)
    if (!m) continue
    const values = m.slice(1).map(translateOne)
    let i = 0
    return en.replace(/\{\}/g, () => values[i++] ?? '')
  }
  return msg
}

/** Traduit un message du serveur dans la langue de l'interface (inchangé en français ou s'il est inconnu). */
export function serverText(msg: string | null | undefined): string {
  if (!msg) return ''
  if (locale.value === 'fr') return msg
  // Les erreurs de validation sont jointes par « ; »
  return msg.split(' ; ').map((part) => translateOne(part.trim())).join('; ')
}
