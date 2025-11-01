<script lang="ts">
  import { onMount } from 'svelte';
  import { items, edges, selectedId, neighborsOfSelected, filters, byId } from '$lib/stores';
  import * as d3 from 'd3';
  export let data;

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

  // For the force graph
  let svgElement: SVGSVGElement;
  
  $: if (svgElement && $selectedId) {
    renderForceGraph();
  }

  function renderForceGraph() {
    if (!svgElement || !$selectedId) return;
    
    const svg = d3.select(svgElement);
    const w = +svg.attr('width');
    const h = +svg.attr('height');
    svg.selectAll('*').remove();

    const center = { id: $selectedId };
    const nodes = [center, ...$neighborsOfSelected.slice(0, 40).map(n => ({ id: n.id, score: n.score }))];
    const links = $neighborsOfSelected.slice(0, 40).map(n => ({ source: $selectedId, target: n.id, weight: n.score }));

    const sim = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links as any).id((d:any)=>d.id).distance(d => 200 - 150*((d as any).weight ?? 0)))
      .force('charge', d3.forceManyBody().strength(-150))
      .force('center', d3.forceCenter(w/2, h/2))
      .on('tick', ticked);

    const link = svg.append('g').selectAll('line')
      .data(links).enter().append('line')
      .attr('stroke', '#aaa')
      .attr('stroke-width', d => 1 + 2*(d.weight ?? 0));

    const circle = svg.append('g').selectAll('circle')
      .data(nodes).enter().append('circle')
      .attr('r', d => d.id === $selectedId ? 8 : 5)
      .attr('fill', d => d.id === $selectedId ? '#000' : '#888')
      .style('cursor','pointer')
      .on('click', (_, d:any) => selectedId.set(d.id));

    const label = svg.append('g').selectAll('text')
      .data(nodes).enter().append('text')
      .text((d:any) => d.id === $selectedId ? 'selected' : '')
      .attr('font-size','10px')
      .attr('fill','#444');

    function ticked(){
      link
        .attr('x1', (d:any)=>d.source.x)
        .attr('y1', (d:any)=>d.source.y)
        .attr('x2', (d:any)=>d.target.x)
        .attr('y2', (d:any)=>d.target.y);

      circle
        .attr('cx',(d:any)=>d.x)
        .attr('cy',(d:any)=>d.y);

      label
        .attr('x',(d:any)=>d.x+6)
        .attr('y',(d:any)=>d.y+3);
    }
  }
</script>

<div class="p-4 grid md:grid-cols-3 gap-4">
  <section class="md:col-span-1 space-y-3">
    <h1 class="text-xl font-semibold">Good Neighbors (Proof of Concept)</h1>

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

      <!-- Force Graph -->
      <div class="border rounded p-2">
        <svg bind:this={svgElement} width="800" height="420"></svg>
      </div>
    {:else}
      <p class="text-gray-600">Select an item on the left to see its "good neighbors."</p>
    {/if}
  </section>
</div>

<style>
  .grid { display: grid; }
</style>
