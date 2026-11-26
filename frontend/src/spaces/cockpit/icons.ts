export interface SimpleIcon {
  s: string
  t: string
  h: string
}

let index: Promise<SimpleIcon[]> | null = null

/** Index Simple Icons (chargé une seule fois, à la demande). */
export function iconIndex(): Promise<SimpleIcon[]> {
  index ??= fetch('/icons/simple/index.json').then((r) => (r.ok ? r.json() : []))
  return index
}

export async function iconColor(slug: string): Promise<string | null> {
  const hit = (await iconIndex()).find((i) => i.s === slug)
  return hit ? `#${hit.h}` : null
}
