<script lang="ts">
  import { onMount } from 'svelte';
  import { items, edges, selectedId, neighborsOfSelected, filters, byId, userInteractions, userSimilarity } from '$lib/stores';
  import NetworkGraph from '$lib/NetworkGraph.svelte';
  import { browser } from '$app/environment';
  export let data;

  import favicon from '$lib/assets/favicon.svg';

  let networkGraph: any;
  let panelOpen = true;
  let hoveredId: string | null = null;
  let hoveredNeighbors: Array<any> = [];
  let NEIGHBOR_WEIGHTS = { text: 0.6, date: 0.2, place: 0.2, user: 0.5 };
  let maxNodes = 500;
  $: currentId = hoveredId ?? $selectedId ?? null;
  let hoverTimer: ReturnType<typeof setTimeout> | null = null;
  // Resizable panel state (desktop)
  let panelWidth = 360; // px
  const PANEL_MIN = 260;
  const PANEL_MAX = 640;
  let isResizing = false;
  let resizeStartX = 0;
  let resizeStartWidth = 0;

  // Expect neighbors JSON as either edge list or {pairs:[{a,b,score}], ...}
  function normalizeNeighbors(n: any) {
    if (Array.isArray(n)) return n; // already [{source,target,score}]
    if (Array.isArray(n?.pairs)) {
      return n.pairs.map((p:any) => ({ source: p.a, target: p.b, score: p.score }));
    }
    // fallback: try {graph:{edges:[...]}}
    return n?.graph?.edges ?? [];
  }

  onMount(() => {
    items.set(data.metadata || []);
    edges.set(normalizeNeighbors(data.neighbors));
    // Set maxNodes to full dataset size by default
    maxNodes = data.metadata?.length || 500;
    if (typeof window !== 'undefined') {
      // Open panel by default on large screens, collapse on small
      panelOpen = window.innerWidth >= 1024; // lg breakpoint
      // Restore saved panel width
      const savedW = Number(localStorage.getItem('ga_panel_width'));
      if (!Number.isNaN(savedW) && savedW >= PANEL_MIN && savedW <= PANEL_MAX) {
        panelWidth = savedW;
      }
    }
  });

  // Persist panelWidth across the session
  $: if (browser) {
    try { localStorage.setItem('ga_panel_width', String(panelWidth)); } catch {}
  }

  let query = '';
  $: q = query.toLowerCase();
  
  // First, filter items based on search/filters (without maxNodes limit)
  $: filteredBySearch = $items.filter(it => {
    const t = (Array.isArray(it.title) ? it.title[0] : it.title) ?? '';
    const okQ = !q || String(t).toLowerCase().includes(q);
    const lang = (it.language && it.language[0]) || '';
    const okLang = !$filters.lang || lang === $filters.lang;
    const y = Number(it.year);
    const okYear =
      (!$filters.yearFrom || y >= $filters.yearFrom) &&
      (!$filters.yearTo   || y <= $filters.yearTo   || Number.isNaN(y));
    return okQ && okLang && okYear;
  });
  
  // Items to show in network: filtered items limited by maxNodes
  $: itemsForNetwork = filteredBySearch.slice(0, maxNodes);
  
  // Set of visible items in network (for syncing the list)
  $: visibleInNetwork = new Set(itemsForNetwork.map(it => it.id));
  
  // Final filtered list (same as filteredBySearch, but can be limited for display)
  $: filtered = filteredBySearch.filter(it => visibleInNetwork.has(it.id));

  function handleNodeClick(id: string) {
    // Empty string signals clear selection
    if (id === '') {
      selectedId.set(null);
    } else {
      // Cancel any pending hover timer to avoid double counting
      if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
      selectedId.set(id);
      // Track view when a node is selected
      userInteractions.trackView(id);
    }
  }

  function handleNodeHover(id: string | null) {
    // Clear any existing timer when hover target changes or clears
    if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; }
    hoveredId = id;
    // Track hover-intent (analytics) after 1s without affecting personalization
    if (id) {
      const lockedId = id; // capture for timer closure
      hoverTimer = setTimeout(() => {
        // Only act if still hovering the same node
        if (hoveredId === lockedId) {
          userInteractions.trackHover(lockedId);
          // Pin details so preview persists despite layout changes
          selectedId.set(lockedId);
        }
        hoverTimer = null;
      }, 3000); // 3s hover-intent
    }
  }

  // Panel resizing handlers (desktop only)
  function startResize(e: MouseEvent | TouchEvent) {
    if (!panelOpen) return;
    isResizing = true;
    resizeStartX = 'touches' in e ? e.touches[0].clientX : e.clientX;
    resizeStartWidth = panelWidth;
    window.addEventListener('mousemove', onResizeMove);
    window.addEventListener('touchmove', onResizeMove as any, { passive: false });
    window.addEventListener('mouseup', endResize);
    window.addEventListener('touchend', endResize as any);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }

  function onResizeMove(e: MouseEvent | TouchEvent) {
    if (!isResizing) return;
    if ('preventDefault' in e) { try { (e as any).preventDefault(); } catch {} }
    const clientX = 'touches' in e ? e.touches[0].clientX : (e as MouseEvent).clientX;
    const delta = resizeStartX - clientX; // drag left (smaller X) => increase width
    const next = Math.max(PANEL_MIN, Math.min(PANEL_MAX, resizeStartWidth + delta));
    panelWidth = next;
  }

  function endResize() {
    isResizing = false;
    window.removeEventListener('mousemove', onResizeMove);
    window.removeEventListener('touchmove', onResizeMove as any);
    window.removeEventListener('mouseup', endResize);
    window.removeEventListener('touchend', endResize as any);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  // Compute neighbors for the hovered node with item details
  function getNeighborsFor(id: string | null, max = 10) {
    if (!id) return [];
    const neighMap = data?.neighbors as any;
    const list = Array.isArray(neighMap)
      ? [] // can't compute detailed neighbors from edge list
      : (neighMap?.[id] ?? []);
    return list
      .slice(0, max)
      .map((n: any) => ({
        ...n,
        item: $byId.get(n.id)
      }));
  }

  $: hoveredNeighbors = getNeighborsFor(currentId, 10);

</script>

<!-- Page Introduction -->
<div class="p-4 space-y-4">
  <div class="flex justify-between items-center">
    <h2 class="text-sm text-gray-600">A Conceptual Visualization of the Graphical Topology of the Archive</h2>
  </div>
  <div class="border-t pt-4">
  <p class="text-md text-gray-600 mb-3">
    This visualization sketches what we are calling the "graphical topology" of the archive: 
    a space where items relate to one another through textual metadata, dates, places, and 
    patterns of interaction. It is not a working archival platform but a conceptual model 
    meant to explore how archives might be navigated through relational proximity rather 
    than fixed hierarchies or linear search.
  </p>

</div>


<!-- Network Visualization View -->
<div class="border rounded-lg bg-white p-4 space-y-3">
    <!-- Network Size Control -->
    <details class="border rounded-lg bg-gray-50" open>
      <summary class="cursor-pointer p-4 select-none font-semibold text-gray-700 text-sm hover:bg-gray-100 rounded-lg">
        <span class="inline-flex items-center justify-between w-full">
          <span>Network Size</span>
          <span class="font-mono font-semibold text-gray-600">{Math.min(maxNodes, filteredBySearch.length)} / {filteredBySearch.length} nodes</span>
        </span>
      </summary>
      <div class="px-4 pb-4 space-y-2">
        <div class="flex items-center gap-3">
          <span class="text-xs text-gray-600">10</span>
          <input 
            type="range" 
            min="10" 
            max={Math.max(10, filteredBySearch.length)} 
            step="10" 
            bind:value={maxNodes}
            class="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span class="text-xs text-gray-600">{filteredBySearch.length}</span>
        </div>
        <p class="text-[10px] text-gray-500">Control the number of nodes from filtered results. Adjust search/filters above to change available items.</p>
      </div>
    </details>

    <!-- Weight Sliders -->
    <details class="border rounded-lg bg-gray-50" open>
      <summary class="cursor-pointer p-4 select-none hover:bg-gray-100 rounded-lg">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-gray-700">Similarity Weights</h3>
          <button
            class="px-3 py-1 text-xs rounded border bg-white hover:bg-gray-100 text-gray-700"
            on:click|stopPropagation={() => { NEIGHBOR_WEIGHTS = { text: 0.6, date: 0.2, place: 0.2, user: 0.5 }; }}
            title="Reset weights to default values">
            Reset Weights
          </button>
        </div>
      </summary>
      <div class="px-4 pb-4">
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Text Weight -->
        <div class="space-y-1">
          <label class="flex items-center justify-between text-xs text-gray-600">
            <span class="inline-flex items-center gap-1">
              <span class="inline-block w-2 h-2 bg-indigo-500 rounded"></span>
              Text
            </span>
            <span class="font-mono font-semibold">{NEIGHBOR_WEIGHTS.text.toFixed(2)}</span>
          </label>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05" 
            bind:value={NEIGHBOR_WEIGHTS.text}
            class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
        </div>

        <!-- Date Weight -->
        <div class="space-y-1">
          <label class="flex items-center justify-between text-xs text-gray-600">
            <span class="inline-flex items-center gap-1">
              <span class="inline-block w-2 h-2 bg-emerald-500 rounded"></span>
              Date
            </span>
            <span class="font-mono font-semibold">{NEIGHBOR_WEIGHTS.date.toFixed(2)}</span>
          </label>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05" 
            bind:value={NEIGHBOR_WEIGHTS.date}
            class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>

        <!-- Place Weight -->
        <div class="space-y-1">
          <label class="flex items-center justify-between text-xs text-gray-600">
            <span class="inline-flex items-center gap-1">
              <span class="inline-block w-2 h-2 bg-amber-500 rounded"></span>
              Place
            </span>
            <span class="font-mono font-semibold">{NEIGHBOR_WEIGHTS.place.toFixed(2)}</span>
          </label>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05" 
            bind:value={NEIGHBOR_WEIGHTS.place}
            class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
        </div>

        <!-- User Weight -->
        <div class="space-y-1">
          <label class="flex items-center justify-between text-xs text-gray-600">
            <span class="inline-flex items-center gap-1">
              <span class="inline-block w-2 h-2 bg-purple-500 rounded"></span>
              User
            </span>
            <span class="font-mono font-semibold">{NEIGHBOR_WEIGHTS.user.toFixed(2)}</span>
          </label>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05" 
            bind:value={NEIGHBOR_WEIGHTS.user}
            class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-purple-500"
          />
        </div>
      </div>
        <p class="text-[10px] text-gray-500 mt-2">Adjust weights to control how similarity scores are calculated: G = {NEIGHBOR_WEIGHTS.text.toFixed(2)}·Text + {NEIGHBOR_WEIGHTS.date.toFixed(2)}·Date + {NEIGHBOR_WEIGHTS.place.toFixed(2)}·Place + {NEIGHBOR_WEIGHTS.user.toFixed(2)}·User</p>
      </div>
    </details>

    <!-- Control Buttons -->
    <div class="flex gap-4 items-center flex-wrap">
      <button 
        class="px-3 py-1 bg-gray-600 text-white rounded text-sm"
        on:click={() => networkGraph?.resetZoom()}>
        Reset Zoom
      </button>

      <button
        class="ml-auto px-3 py-1 rounded text-sm border bg-gray-100 hover:bg-gray-200"
        aria-controls="preview-panel"
        aria-expanded={panelOpen}
        on:click={() => (panelOpen = !panelOpen)}>
        {panelOpen ? 'Hide panel' : 'Show panel'}
      </button>

      <button
        class="px-3 py-1 rounded text-sm border bg-red-50 hover:bg-red-100 text-red-700"
        title="Reset interaction history"
        on:click={() => { if(confirm('Clear all tracked views and bookmarks?')) userInteractions.reset(); }}>
        Reset Interactions
      </button>
    </div>

    <div class="flex flex-col lg:flex-row gap-4 items-start">
      <!-- Left Column: Graph + Search & Filter -->
      <div class="flex-1 min-w-0 space-y-4">
        <!-- Network Graph -->
        {#if browser}
          <NetworkGraph 
            bind:this={networkGraph}
            items={itemsForNetwork}
            neighbors={data.neighbors}
            userSimilarity={$userSimilarity}
            textWeight={NEIGHBOR_WEIGHTS.text}
            dateWeight={NEIGHBOR_WEIGHTS.date}
            placeWeight={NEIGHBOR_WEIGHTS.place}
            userWeight={NEIGHBOR_WEIGHTS.user}
            maxNodes={maxNodes}
            selectedId={$selectedId}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
          />
        {:else}
          <div class="h-[600px] flex items-center justify-center text-gray-500">
            Loading client view…
          </div>
        {/if}

        <!-- Search & Filter Section -->
        <div class="border rounded-lg bg-white p-4">
          <h3 class="text-lg font-bold text-gray-800 mb-3">Search & Filter</h3>
          
          <div class="space-y-3">
            <div class="flex gap-3 flex-wrap items-center">
              <input type="search" class="border rounded px-3 py-2 flex-1 min-w-[200px]" placeholder="Search title…" bind:value={query} />

              <select class="border rounded px-3 py-2" on:change={(e)=>filters.set({...$filters, lang: (e.target as HTMLSelectElement).value || undefined})}>
                <option value="">All languages</option>
                {#each Array.from(new Set($items.flatMap(it => it.language || []))) as lng}
                  <option value={lng}>{lng}</option>
                {/each}
              </select>

              <input class="border rounded px-3 py-2 w-32" type="number" placeholder="Year ≥"
                on:change={(e)=>filters.set({...$filters, yearFrom: Number((e.target as HTMLInputElement).value)||undefined})} />
              <input class="border rounded px-3 py-2 w-32" type="number" placeholder="Year ≤"
                on:change={(e)=>filters.set({...$filters, yearTo: Number((e.target as HTMLInputElement).value)||undefined})} />
            </div>

            <div class="text-sm text-gray-600">
              Showing {Math.min(filtered.length, 200)} of {filtered.length} items
            </div>

            <ul class="border rounded divide-y max-h-[50vh] overflow-auto bg-gray-50">
              {#each filtered.slice(0, 200) as it}
                <li class="p-0">
                  <button
                    type="button"
                    class="w-full text-left p-3 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 {$selectedId === it.id ? 'bg-blue-50' : ''}"
                    on:click={() => { selectedId.set(it.id); if (networkGraph) networkGraph.centerOnNode?.(it.id); }}
                  >
                    <div class="text-sm font-medium">{Array.isArray(it.title) ? it.title[0] : it.title}</div>
                    <div class="text-xs text-gray-500">{it.year} · {(it.language && it.language.join(', ')) || ''}</div>
                  </button>
                </li>
              {/each}
            </ul>
          </div>
        </div>
      </div>

      <!-- Right Column: Vertical resizer + Detail Panel -->
      <!-- Vertical resizer: visible on desktop when panel is open -->
      <div
        role="separator"
        aria-orientation="vertical"
        class="hidden lg:block w-1 cursor-col-resize self-stretch bg-gray-300 hover:bg-gray-400 transition-colors"
        aria-hidden={!panelOpen}
        on:mousedown={startResize}
        on:touchstart={startResize}
        title="Drag to resize details panel"
      ></div>

      <aside
        id="preview-panel"
        class="border rounded-lg p-3 bg-gray-50 max-h-[140vh] overflow-auto w-full lg:w-auto flex-shrink-0 {panelOpen ? 'block' : 'hidden'}"
        aria-hidden={!panelOpen}
        style="width: {panelOpen ? panelWidth + 'px' : 'auto'}"
      >
        <h3 class="font-semibold mb-2">Details</h3>
        {#if currentId && $byId.get(currentId)}
          {@const it = $byId.get(currentId)!}
          {@const title = Array.isArray(it.title) ? it.title[0] : it.title}
          {#if it.thumbnail}
            <img src={it.thumbnail} alt={title || 'thumbnail'} class="w-full h-auto rounded mb-2" />
          {/if}
          <div class="space-y-1">
            <div class="font-medium">{title ?? '(no title)'}</div>
            <div class="text-xs text-gray-600">{it.year ?? ''} · {(it.language && it.language.join(', ')) || ''}</div>
            {#if it.country}
              <div class="text-xs">Country: {it.country}</div>
            {/if}
            {#if it.collection}
              <div class="text-xs">Collection: {it.collection}</div>
            {/if}
            {#if it.link}
              <a href={it.link} target="_blank" class="text-blue-600 text-sm hover:underline">View on Europeana</a>
            {/if}
            <!-- Bookmark toggle -->
            <button 
              class="mt-2 px-2 py-1 text-xs rounded {$userInteractions.bookmarks.has(currentId) ? 'bg-yellow-100 text-yellow-800 border border-yellow-300' : 'bg-gray-100 text-gray-700 border border-gray-300'}"
              on:click={() => userInteractions.toggleBookmark(currentId)}>
              {$userInteractions.bookmarks.has(currentId) ? '★ Bookmarked' : '☆ Bookmark'}
            </button>
            <!-- Hover analytics (does not affect personalization) -->
            <div class="text-[11px] text-gray-500 mt-1">
              Hover views: {($userInteractions.hoverTimestamps?.get(currentId)?.length) || 0}
            </div>
          </div>

          <!-- Neighbor list with similarity breakdown -->
          {#if hoveredNeighbors.length}
            <div class="mt-4 border-t pt-3">
              <div class="flex items-center justify-between mb-2">
                <h4 class="font-semibold">Top neighbors</h4>
                <span class="text-[10px] text-gray-500">G = {NEIGHBOR_WEIGHTS.text}·Text + {NEIGHBOR_WEIGHTS.date}·Date + {NEIGHBOR_WEIGHTS.place}·Place + {NEIGHBOR_WEIGHTS.user}·User</span>
              </div>
              <ul class="divide-y">
                {#each hoveredNeighbors as n}
                  {@const t = Array.isArray(n.item?.title) ? n.item?.title[0] : n.item?.title}
                  {@const userScore = $userSimilarity.get([currentId, n.id].sort().join('|')) ?? 0}
                  {@const adjustedScore = NEIGHBOR_WEIGHTS.text * (n.S_text ?? 0) + NEIGHBOR_WEIGHTS.date * (n.S_date ?? 0) + NEIGHBOR_WEIGHTS.place * (n.S_place ?? 0) + NEIGHBOR_WEIGHTS.user * userScore}
                  <li class="py-2">
                    <div class="flex items-start justify-between gap-2">
                      <button class="text-left text-sm hover:underline" on:click={() => { selectedId.set(n.id); hoveredId = null; }}>
                        {t ?? n.title ?? n.id}
                      </button>
                      <span class="text-xs text-gray-600 whitespace-nowrap">
                        {adjustedScore.toFixed(2)}
                        {#if userScore > 0}<span class="text-purple-600 ml-1" title="User interaction boost">↑</span>{/if}
                      </span>
                    </div>
                    <div class="mt-1">
                      <div class="flex items-center gap-2 text-[11px] text-gray-600 flex-wrap">
                        <span class="inline-flex items-center gap-1"><span class="inline-block w-2 h-2 bg-indigo-500 rounded"></span>Text {Number(n.S_text ?? 0).toFixed(2)}</span>
                        <span class="inline-flex items-center gap-1"><span class="inline-block w-2 h-2 bg-emerald-500 rounded"></span>Date {Number(n.S_date ?? 0).toFixed(2)}</span>
                        <span class="inline-flex items-center gap-1"><span class="inline-block w-2 h-2 bg-amber-500 rounded"></span>Place {Number(n.S_place ?? 0).toFixed(2)}</span>
                        <span class="inline-flex items-center gap-1 {userScore > 0 ? 'text-purple-600 font-medium' : ''}"><span class="inline-block w-2 h-2 bg-purple-500 rounded"></span>User {userScore.toFixed(2)}</span>
                      </div>
                      
                    </div>
                  </li>
                {/each}
              </ul>
            </div>
          {/if}
        {:else}
          <p class="text-sm text-gray-600">Hover a node to preview it; click a node to keep it here until you hover another.</p>
        {/if}
      </aside>
    </div>
  </div>
</div>