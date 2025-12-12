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

  // Accordion state management
  let detailsRefs: HTMLDetailsElement[] = [];
  let allExpanded = false;

  function toggleAllDetails() {
    allExpanded = !allExpanded;
    detailsRefs.forEach(details => {
      if (details) details.open = allExpanded;
    });
  }

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

<div class="p-4 space-y-4">
  <div class="flex justify-between items-center">
    <h1 class="text-2xl font-bold">Graphical Archive</h1>
    <h2 class="text-sm text-gray-600">A Conceptual Visualization of the Graphical Topology of the Archive</h2>
    
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
  <div class="border-t pt-4">
  <p class="text-md text-gray-600 mb-3">
    This visualization sketches what we are calling the "graphical topology" of the archive: 
    a space where items relate to one another through textual metadata, dates, places, and 
    patterns of interaction. It is not a working archival platform but a conceptual model 
    meant to explore how archives might be navigated through relational proximity rather 
    than fixed hierarchies or linear search.
  </p>

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

{#if showNetworkView}
<!-- About Section: Timeline/Stepped Layout -->
<div class="mt-12 border-t-2 pt-8 bg-gradient-to-b from-gray-50 to-white">
  <div class="max-w-6xl mx-auto">
    <div class="text-center mb-8">
      <h2 class="text-3xl font-bold text-gray-800 mb-2">Understanding the Visualization</h2>
      <p class="text-gray-600">Follow the journey from concept to interaction</p>
    </div>

    <!-- Timeline Container -->
    <div class="relative">
      <!-- Vertical connecting line (hidden on mobile, visible on larger screens) -->
      <div class="hidden md:block absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-400 via-green-400 via-purple-400 to-amber-400"></div>

      <!-- Step 1: What -->
      <div class="relative mb-8 md:mb-12">
        <div class="flex flex-col md:flex-row gap-4 items-start">
          <!-- Number badge -->
          <div class="flex-shrink-0 w-16 h-16 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white font-bold text-xl shadow-lg z-10">
            <span class="text-2xl">👁️</span>
          </div>
          
          <!-- Content card -->
          <div class="flex-1 bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow duration-300 border-l-4 border-blue-400">
            <details bind:this={detailsRefs[0]} open class="group">
              <summary class="cursor-pointer p-6 select-none flex items-center justify-between">
                <div>
                  <div class="flex items-center gap-3 mb-1">
                    <span class="text-xs font-semibold text-blue-600 uppercase tracking-wider">Step 1</span>
                    <span class="text-gray-400">→</span>
                  </div>
                  <h3 class="text-xl font-bold text-gray-800">What are you seeing here?</h3>
                  <p class="text-sm text-gray-500 mt-1">Discover the topology of connections</p>
                </div>
                <span class="text-gray-400 text-xl group-open:rotate-180 transition-transform duration-300">▼</span>
              </summary>
              <div class="px-6 pb-6 text-gray-600 space-y-3 animate-fadeIn border-t pt-4">
                <p>
                  Each node is an abstract representation of an archival item (digital object + digital 
                  artifact). Edges indicate similarity based on metadata such as titles, dates, places, 
                  or themes. Clusters emerge where items share multiple attributes, forming 
                  "neighborhoods" of related material.
                </p>
                <p>
                  These neighborhoods shift as you interact with the archive: items you view, bookmark, 
                  or hover over influence the layout, bringing similar nodes closer to your focus. 
                  This simulates a personalized exploration of the archive—one in which your interests 
                  and questions shape the connections you see, surfacing related items that might remain 
                  hidden in traditional search or browsing workflows.
                </p>
              </div>
            </details>
          </div>
        </div>
      </div>

      <!-- Step 2: How -->
      <div class="relative mb-8 md:mb-12">
        <div class="flex flex-col md:flex-row gap-4 items-start">
          <div class="flex-shrink-0 w-16 h-16 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center text-white font-bold text-xl shadow-lg z-10">
            <span class="text-2xl">🤔</span>
          </div>
          
          <div class="flex-1 bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow duration-300 border-l-4 border-green-400">
            <details bind:this={detailsRefs[1]} class="group">
              <summary class="cursor-pointer p-6 select-none flex items-center justify-between">
                <div>
                  <div class="flex items-center gap-3 mb-1">
                    <span class="text-xs font-semibold text-green-600 uppercase tracking-wider">Step 2</span>
                    <span class="text-gray-400">→</span>
                  </div>
                  <h3 class="text-xl font-bold text-gray-800">How to use it?</h3>
                  <p class="text-sm text-gray-500 mt-1">Navigate and interact with the archive</p>
                </div>
                <span class="text-gray-400 text-xl group-open:rotate-180 transition-transform duration-300">▼</span>
              </summary>
              <div class="px-6 pb-6 text-gray-600 space-y-3 animate-fadeIn border-t pt-4">
                <p>
                  In Network View, hover over nodes to preview item details in the side panel; click a 
                  node to pin it there. Use the search and filter panel to locate specific items or narrow 
                  the view. The graph adjusts dynamically based on your interactions, highlighting items 
                  similar to those you engage with.
                </p>
                <p>
                  From the details panel, you can bookmark items for later reference; these bookmarks 
                  also influence the layout, bringing related materials closer to your attention. You can 
                  explore each item's "top neighbors," with similarity scores broken down by attribute 
                  type. The more you interact, the more the graph adapts to your evolving interests.
                </p>
                <p class="text-sm italic text-gray-500">
                  💡 Tip: You can reset your interaction history at any time to start fresh.
                </p>
              </div>
            </details>
          </div>
        </div>
      </div>

      <!-- Step 3: Privacy -->
      <div class="relative mb-8 md:mb-12">
        <div class="flex flex-col md:flex-row gap-4 items-start">
          <div class="flex-shrink-0 w-16 h-16 rounded-full bg-gradient-to-br from-purple-400 to-pink-500 flex items-center justify-center text-white font-bold text-xl shadow-lg z-10">
            <span class="text-2xl">📊</span>
          </div>
          
          <div class="flex-1 bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow duration-300 border-l-4 border-purple-400">
            <details bind:this={detailsRefs[2]} class="group">
              <summary class="cursor-pointer p-6 select-none flex items-center justify-between">
                <div>
                  <div class="flex items-center gap-3 mb-1">
                    <span class="text-xs font-semibold text-purple-600 uppercase tracking-wider">Step 3</span>
                    <span class="text-gray-400">→</span>
                  </div>
                  <h3 class="text-xl font-bold text-gray-800">What about my data?</h3>
                  <p class="text-sm text-gray-500 mt-1">Your privacy and data security</p>
                </div>
                <span class="text-gray-400 text-xl group-open:rotate-180 transition-transform duration-300">▼</span>
              </summary>
              <div class="px-6 pb-6 text-gray-600 space-y-3 animate-fadeIn border-t pt-4">
                <p>
                  Your interactions (views, hovers, bookmarks) are stored locally in your browser and 
                  are never transmitted to any server. This keeps your exploration private and 
                  personalized without external tracking.
                </p>
                <p>
                  It also means your history will disappear if you clear your browser data or switch 
                  devices. This is a conceptual demo meant to prototype new modes of archival navigation, 
                  not a production platform.
                </p>
              </div>
            </details>
          </div>
        </div>
      </div>

      <!-- Step 4: Why -->
      <div class="relative">
        <div class="flex flex-col md:flex-row gap-4 items-start">
          <div class="flex-shrink-0 w-16 h-16 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-bold text-xl shadow-lg z-10">
            <span class="text-2xl">✳</span>
          </div>
          
          <div class="flex-1 bg-white rounded-xl shadow-md hover:shadow-xl transition-shadow duration-300 border-l-4 border-amber-400">
            <details bind:this={detailsRefs[3]} class="group">
              <summary class="cursor-pointer p-6 select-none flex items-center justify-between">
                <div>
                  <div class="flex items-center gap-3 mb-1">
                    <span class="text-xs font-semibold text-amber-600 uppercase tracking-wider">Step 4</span>
                    <span class="text-gray-400">🕸️</span>
                  </div>
                  <h3 class="text-xl font-bold text-gray-800">Why this visualization?</h3>
                  <p class="text-sm text-gray-500 mt-1">The conceptual foundation</p>
                </div>
                <span class="text-gray-400 text-xl group-open:rotate-180 transition-transform duration-300">▼</span>
              </summary>
              <div class="px-6 pb-6 text-gray-600 space-y-3 animate-fadeIn border-t pt-4">
                <p>
                  Digital concepts are hard to grasp narratively. Technical jargon and algorithmic 
                  formulas often obscure more than they clarify, and recommendation systems can feel 
                  like black boxes even to their creators.
                </p>
                <p>
                  By visualizing the relational topology of an archive, and allowing users to see how 
                  their interactions reshape that topology, this project aims to demystify how digital 
                  archives suggest, relate, and connect items. The visualization invites reflection on 
                  how meaning is constructed through adjacency and traversal, challenging traditional 
                  notions of archival organization and navigation.
                </p>
              </div>
            </details>
          </div>
        </div>
      </div>
    </div>

    <!-- Expand All Toggle -->
    <div class="flex justify-center mt-8">
      <button
        on:click={toggleAllDetails}
        class="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm font-medium transition-colors shadow-sm hover:shadow-md"
      >
        {allExpanded ? '▲ Collapse All Steps' : '▼ Expand All Steps'}
      </button>
    </div>
  </div>
</div>
{/if}
</div>

<style>
  .grid { display: grid; }
  
  /* Fade-in animation for accordion content */
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .animate-fadeIn {
    animation: fadeIn 0.3s ease-out forwards;
  }
  
  /* Smooth details marker animation */
  details summary::-webkit-details-marker {
    display: none;
  }
  
  details summary::marker {
    display: none;
  }
  
  /* Enhanced hover effects */
  details:hover {
    transform: translateY(-2px);
  }
</style>

