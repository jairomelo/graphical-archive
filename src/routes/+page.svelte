<script lang="ts">
  import { onMount } from 'svelte';
  import { items, edges, selectedId, neighborsOfSelected, filters, byId, userInteractions, userSimilarity } from '$lib/stores';
  import NetworkGraph from '$lib/NetworkGraph.svelte';
  import { browser } from '$app/environment';
  export let data;

  let showNetworkView = true;
  let networkGraph: any;
  let panelOpen = true;
  let hoveredId: string | null = null;
  let hoveredNeighbors: Array<any> = [];
  const NEIGHBOR_WEIGHTS = { text: 0.6, date: 0.2, place: 0.2, user: 0.5 };
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
  $: filtered = $items.filter(it => {
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
      hoverTimer = setTimeout(() => {
        userInteractions.trackHover(id);
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

<div class="p-4 space-y-4">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold">Europeana Network Visualization</h1>
    
    <div class="flex gap-2">
      <button 
        class="px-4 py-2 rounded {showNetworkView ? 'bg-blue-600 text-white' : 'bg-gray-200'}"
        on:click={() => showNetworkView = true}>
        Network View
      </button>
      <button 
        class="px-4 py-2 rounded {!showNetworkView ? 'bg-blue-600 text-white' : 'bg-gray-200'}"
        on:click={() => showNetworkView = false}>
        List View
      </button>
    </div>
  </div>

{#if showNetworkView}
  <!-- Network Visualization View -->
  <div class="border rounded-lg bg-white p-4 space-y-3">
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
      <div class="flex-1 min-w-0">
        {#if browser}
          <NetworkGraph 
            bind:this={networkGraph}
            items={$items}
            neighbors={data.neighbors}
            userSimilarity={$userSimilarity}
            userWeight={NEIGHBOR_WEIGHTS.user}
            selectedId={$selectedId}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
          />
        {:else}
          <div class="h-[600px] flex items-center justify-center text-gray-500">
            Loading client view…
          </div>
        {/if}
      </div>

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
        class="border rounded-lg p-3 bg-gray-50 max-h-[80vh] overflow-auto w-full lg:w-auto flex-shrink-0 {panelOpen ? 'block' : 'hidden'}"
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
                  {@const adjustedScore = (n.score ?? 0) + NEIGHBOR_WEIGHTS.user * userScore}
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

{:else}
  <!-- Original List View -->
  <div class="grid md:grid-cols-3 gap-4">
    <section class="md:col-span-1 space-y-3">
      <h2 class="text-lg font-semibold">Search & Filter</h2>

      <input class="border rounded px-2 py-1 w-full" placeholder="Search title…" bind:value={query} />

      <div class="flex gap-2">
        <select class="border rounded px-2 py-1" on:change={(e)=>filters.set({...$filters, lang: (e.target as HTMLSelectElement).value || undefined})}>
          <option value="">All languages</option>
          {#each Array.from(new Set($items.flatMap(it => it.language || []))) as lng}
            <option value={lng}>{lng}</option>
          {/each}
        </select>

        <input class="border rounded px-2 py-1 w-24" type="number" placeholder="Year ≥"
          on:change={(e)=>filters.set({...$filters, yearFrom: Number((e.target as HTMLInputElement).value)||undefined})} />
        <input class="border rounded px-2 py-1 w-24" type="number" placeholder="Year ≤"
          on:change={(e)=>filters.set({...$filters, yearTo: Number((e.target as HTMLInputElement).value)||undefined})} />
      </div>

      <ul class="border rounded divide-y max-h-[50vh] overflow-auto">
        {#each filtered.slice(0, 200) as it}
          <li class="p-0">
            <button
              type="button"
              class="w-full text-left p-2 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              on:click={() => selectedId.set(it.id)}
            >
              <div class="text-sm font-medium">{Array.isArray(it.title) ? it.title[0] : it.title}</div>
              <div class="text-xs text-gray-500">{it.year} · {(it.language && it.language.join(', ')) || ''}</div>
            </button>
          </li>
        {/each}
      </ul>
    </section>

    <section class="md:col-span-2 space-y-4">
      {#if $selectedId}
        <!-- Selected Item -->
        {#if $byId.get($selectedId)}
          {@const it = $byId.get($selectedId)!}
          {@const title = Array.isArray(it.title) ? it.title[0] : it.title}
          <div class="border rounded p-3">
            <div class="text-lg font-semibold">{title ?? '(no title)'}</div>
            <div class="text-sm text-gray-600">{it.year ?? ''} · {(it.language && it.language.join(', ')) || ''}</div>
          </div>
        {:else}
          <div class="text-gray-500">No item found.</div>
        {/if}

        <!-- Neighbors List -->
        <div class="border rounded">
          <div class="px-3 py-2 font-semibold bg-gray-50">Closest neighbors</div>
          <ul class="divide-y max-h-[40vh] overflow-auto">
            {#each $neighborsOfSelected as n}
              {@const t = Array.isArray(n.item?.title) ? n.item?.title[0] : n.item?.title}
              <li class="p-2 flex justify-between items-center">
                <button class="text-left text-sm hover:underline" on:click={() => selectedId.set(n.id)}>
                  {t ?? n.id}
                </button>
                <span class="text-xs text-gray-500">{n.score.toFixed(2)}</span>
              </li>
            {/each}
          </ul>
        </div>
      {:else}
        <p class="text-gray-600">Select an item on the left to see its "good neighbors."</p>
      {/if}
    </section>
  </div>
{/if}
</div>

<style>
  .grid { display: grid; }
</style>
