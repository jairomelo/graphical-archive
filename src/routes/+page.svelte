<script lang="ts">
  import { onMount } from 'svelte';
  import { items, edges, selectedId, neighborsOfSelected, filters, byId } from '$lib/stores';
  import NetworkGraph from '$lib/NetworkGraph.svelte';
  import { browser } from '$app/environment';
  export let data;

  let showNetworkView = true;
  let networkGraph: any;
  let maxNodes = 500;
  let minScore = 0.02;
  let hoveredId: string | null = null;

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
  });

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
    selectedId.set(id);
  }

  function handleNodeHover(id: string | null) {
    hoveredId = id;
  }

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
      <div>
        <label class="text-sm font-medium">Max Nodes:</label>
        <input type="range" min="50" max="2000" step="50" bind:value={maxNodes} class="ml-2" />
        <span class="text-sm ml-2">{maxNodes}</span>
      </div>
      
      <div>
        <label class="text-sm font-medium">Min Score:</label>
        <input type="range" min="0" max="0.1" step="0.01" bind:value={minScore} class="ml-2" />
        <span class="text-sm ml-2">{minScore.toFixed(2)}</span>
      </div>

      <button 
        class="px-3 py-1 bg-gray-600 text-white rounded text-sm"
        on:click={() => networkGraph?.resetZoom()}>
        Reset Zoom
      </button>
      
      <button 
        class="px-3 py-1 bg-gray-600 text-white rounded text-sm"
        on:click={() => networkGraph?.reheat()}>
        Re-simulate
      </button>
    </div>

    <div class="flex gap-4 items-start">
      <div class="flex-1 min-w-0">
        {#if browser}
          <NetworkGraph 
            bind:this={networkGraph}
            items={$items}
            neighbors={data.neighbors}
            {maxNodes}
            {minScore}
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

  <aside class="border rounded-lg p-3 bg-gray-50 max-h-[80vh] overflow-auto w-[360px] flex-shrink-0">
        <h3 class="font-semibold mb-2">Preview</h3>
        {#if hoveredId && $byId.get(hoveredId)}
          {@const h = $byId.get(hoveredId)!}
          {@const title = Array.isArray(h.title) ? h.title[0] : h.title}
          {#if h.thumbnail}
            <img src={h.thumbnail} alt={title || 'thumbnail'} class="w-full h-auto rounded mb-2" />
          {/if}
          <div class="space-y-1">
            <div class="font-medium">{title ?? '(no title)'}</div>
            <div class="text-xs text-gray-600">{h.year ?? ''} · {(h.language && h.language.join(', ')) || ''}</div>
            {#if h.country}
              <div class="text-xs">Country: {h.country}</div>
            {/if}
            {#if h.collection}
              <div class="text-xs">Collection: {h.collection}</div>
            {/if}
            {#if h.place_label}
              <div class="text-xs">Place: {Array.isArray(h.place_label) ? h.place_label.join(', ') : h.place_label}</div>
            {/if}
            {#if h.link}
              <a href={h.link} target="_blank" class="text-blue-600 text-sm hover:underline">View on Europeana</a>
            {/if}
          </div>
        {:else}
          <p class="text-sm text-gray-600">Hover a node to preview its image and metadata.</p>
        {/if}

        {#if $selectedId && $byId.get($selectedId)}
          {@const s = $byId.get($selectedId)!}
          {@const stitle = Array.isArray(s.title) ? s.title[0] : s.title}
          <div class="mt-4 border-t pt-3">
            <h4 class="font-semibold">Selected</h4>
            <div class="text-sm">{stitle ?? '(no title)'}</div>
            <div class="text-xs text-gray-600">{s.year ?? ''} · {(s.language && s.language.join(', ')) || ''}</div>
            {#if s.link}
              <a href={s.link} target="_blank" class="text-blue-600 text-sm hover:underline">Open</a>
            {/if}
          </div>
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
          <li class="p-2 hover:bg-gray-50 cursor-pointer" on:click={() => selectedId.set(it.id)}>
            <div class="text-sm font-medium">{Array.isArray(it.title) ? it.title[0] : it.title}</div>
            <div class="text-xs text-gray-500">{it.year} · {(it.language && it.language.join(', ')) || ''}</div>
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
