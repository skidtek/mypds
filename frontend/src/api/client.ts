import { serverText } from '@/i18n/server'
import { locale, t } from '@/i18n'

/** Client REST : cookie de session (same-origin) + jeton CSRF pour les requêtes non sûres. */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

let csrfToken = ''
let onUnauthorized: (() => void) | null = null

export function setCsrfToken(token: string) {
  csrfToken = token
}

export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

function detailOf(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return serverText(d)
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, '')
  }
  if (status >= 500) return t('Le serveur ne répond pas correctement. Réessayez dans un instant.')
  return t('Erreur {status}', { status })
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  let body = init.body
  if (init.json !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(init.json)
  }
  headers.set('Accept-Language', locale.value)
  if (!['GET', 'HEAD'].includes(method) && csrfToken) headers.set('X-CSRF-Token', csrfToken)
  let res: Response
  try {
    res = await fetch(path, { ...init, method, headers, body, credentials: 'same-origin' })
  } catch {
    throw new ApiError(0, t('Connexion au serveur impossible.'))
  }
  if (res.status === 204) return undefined as T
  const isJson = res.headers.get('content-type')?.includes('json')
  const data = isJson ? await res.json() : await res.text()
  if (!res.ok) {
    if (res.status === 401 && !path.endsWith('/auth/login')) onUnauthorized?.()
    throw new ApiError(res.status, detailOf(data, res.status))
  }
  return data as T
}
