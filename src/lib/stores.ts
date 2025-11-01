import { writable, derived } from 'svelte/store';

export type Item = {
  id: string;
  title?: string[] | string;
  year?: string;
  language?: string[];
  place_lat?: string | null;
  place_lon?: string | null;
  type?: string;
  collection?: string;
  description?: string[] | string;
  creator?: string[];
  concepts?: string[];
  country?: string;
  thumbnail?: string;
  link?: string;
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

// User interaction tracking (session-based, no server)
export type UserInteraction = {
  views: Set<string>;
  bookmarks: Set<string>;
  viewTimestamps: Map<string, number[]>; // track when each item was viewed
};

function loadInteractions(): UserInteraction {
  if (typeof window === 'undefined') return { views: new Set(), bookmarks: new Set(), viewTimestamps: new Map() };
  try {
    const stored = sessionStorage.getItem('europeana_user_interactions');
    if (!stored) return { views: new Set(), bookmarks: new Set(), viewTimestamps: new Map() };
    const parsed = JSON.parse(stored);
    return {
      views: new Set(parsed.views || []),
      bookmarks: new Set(parsed.bookmarks || []),
      viewTimestamps: new Map(parsed.viewTimestamps || [])
    };
  } catch {
    return { views: new Set(), bookmarks: new Set(), viewTimestamps: new Map() };
  }
}

function saveInteractions(data: UserInteraction) {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem('europeana_user_interactions', JSON.stringify({
      views: Array.from(data.views),
      bookmarks: Array.from(data.bookmarks),
      viewTimestamps: Array.from(data.viewTimestamps.entries())
    }));
  } catch (e) {
    console.warn('Failed to save interactions:', e);
  }
}

function createInteractionStore() {
  const { subscribe, update } = writable<UserInteraction>(loadInteractions());

  return {
    subscribe,
    trackView: (id: string) => update(state => {
      state.views.add(id);
      const timestamps = state.viewTimestamps.get(id) || [];
      timestamps.push(Date.now());
      state.viewTimestamps.set(id, timestamps);
      saveInteractions(state);
      return state;
    }),
    toggleBookmark: (id: string) => update(state => {
      if (state.bookmarks.has(id)) {
        state.bookmarks.delete(id);
      } else {
        state.bookmarks.add(id);
      }
      saveInteractions(state);
      return state;
    }),
    reset: () => update(() => {
      const fresh = { views: new Set<string>(), bookmarks: new Set<string>(), viewTimestamps: new Map<string, number[]>() };
      saveInteractions(fresh);
      return fresh;
    })
  };
}

export const userInteractions = createInteractionStore();

// Compute user-based similarity: S_user(i,j) based on co-occurrence in views/bookmarks
export const userSimilarity = derived(
  [userInteractions],
  ([$interactions]) => {
    const viewList = Array.from($interactions.views);
    const bookmarkList = Array.from($interactions.bookmarks);
    
    // Build co-occurrence map: how often pairs appear together
    const coViews = new Map<string, number>();
    const coBookmarks = new Map<string, number>();
    
    // For views: sliding window co-occurrence (items viewed close in time)
    const viewArray = Array.from($interactions.viewTimestamps.entries())
      .sort((a, b) => {
        const aLast = a[1][a[1].length - 1] || 0;
        const bLast = b[1][b[1].length - 1] || 0;
        return aLast - bLast;
      })
      .map(e => e[0]);
    
    // Co-view: items viewed within same session window (consecutive views)
    const windowSize = 5;
    for (let i = 0; i < viewArray.length; i++) {
      for (let j = i + 1; j < Math.min(i + windowSize, viewArray.length); j++) {
        const key = [viewArray[i], viewArray[j]].sort().join('|');
        coViews.set(key, (coViews.get(key) || 0) + 1);
      }
    }
    
    // Co-bookmark: all pairs of bookmarked items
    for (let i = 0; i < bookmarkList.length; i++) {
      for (let j = i + 1; j < bookmarkList.length; j++) {
        const key = [bookmarkList[i], bookmarkList[j]].sort().join('|');
        coBookmarks.set(key, (coBookmarks.get(key) || 0) + 1);
      }
    }
    
    // Compute S_user scores (normalized by max possible co-occurrence)
    const scores = new Map<string, number>();
    const maxCoView = Math.max(1, ...Array.from(coViews.values()));
    const maxCoBookmark = Math.max(1, ...Array.from(coBookmarks.values()));
    
    coViews.forEach((count, key) => {
      scores.set(key, (scores.get(key) || 0) + 0.4 * (count / maxCoView));
    });
    
    coBookmarks.forEach((count, key) => {
      scores.set(key, (scores.get(key) || 0) + 0.6 * (count / maxCoBookmark));
    });
    
    return scores;
  }
);
