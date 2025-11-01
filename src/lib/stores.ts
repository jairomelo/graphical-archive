import { writable, derived } from 'svelte/store';

export type Item = {
  id: string;
  title?: string[] | string;
  year?: string;
  language?: string[];  // etc. keep loose for now
  place_lat?: string | null;
  place_lon?: string | null;
  // ...
};

export type NeighborEdge = { source: string; target: string; score: number };

export const items = writable<Item[]>([]);
export const byId = derived(items, ($items) => {
  const m = new Map<string, Item>();
  for (const it of $items) m.set(it.id, it);
  return m;
});

export const edges = writable<NeighborEdge[]>([]);

export const selectedId = writable<string | null>(null);
export const filters = writable<{ lang?: string; yearFrom?: number; yearTo?: number }>({});

export const neighborsOfSelected = derived(
  [selectedId, edges, byId],
  ([$selectedId, $edges, $byId]) => {
    if (!$selectedId) return [];
    return $edges
      .filter(e => e.source === $selectedId || e.target === $selectedId)
      .map(e => ({
        id: e.source === $selectedId ? e.target : e.source,
        score: e.score,
        item: $byId.get(e.source === $selectedId ? e.target : e.source)
      }))
      .filter(n => n.item)
      .sort((a, b) => b.score - a.score);
  }
);
