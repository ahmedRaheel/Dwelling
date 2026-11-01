/** A device-local, non-sensitive shortlist. No property data is persisted. */
const KEY = 'dwelling_compare_ids';
const EVENT = 'dwelling-compare-changed';

export function comparisonIds(): string[] {
  try {
    const ids: unknown = JSON.parse(sessionStorage.getItem(KEY) ?? '[]');
    return Array.isArray(ids) ? ids.filter((id): id is string => typeof id === 'string').slice(0, 4) : [];
  } catch { return []; }
}

export function toggleComparison(id: string): boolean {
  const previous = comparisonIds();
  if (previous.includes(id)) {
    sessionStorage.setItem(KEY, JSON.stringify(previous.filter(entry => entry !== id)));
    window.dispatchEvent(new Event(EVENT));
    return false;
  }
  if (previous.length >= 4) throw new Error('Compare up to four properties at a time.');
  sessionStorage.setItem(KEY, JSON.stringify([...previous, id]));
  window.dispatchEvent(new Event(EVENT));
  return true;
}

export const COMPARE_EVENT = EVENT;
