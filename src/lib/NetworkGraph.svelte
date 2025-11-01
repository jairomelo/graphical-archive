<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  // @ts-ignore - d3 types issue
  import * as d3 from 'd3';
  import type { Item, NeighborEdge } from './stores';

  type GraphNode = {
    id: string;
    title: string;
    year?: string;
    type?: string;
    collection?: string;
    degree: number;
    cluster: number;
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    fx?: number | null;
    fy?: number | null;
  };

  type GraphLink = {
    source: string | GraphNode;
    target: string | GraphNode;
    score: number;
    S_text?: number;
    S_date?: number;
    S_place?: number;
  };

  export let items: Item[] = [];
  export let neighbors: Record<string, any[]> = {};
  export let onNodeClick: (id: string) => void = () => {};
  export let onNodeHover: (id: string | null) => void = () => {};
  export let selectedId: string | null = null;
  export let maxNodes: number = 500;
  export let minScore: number = 0.02;

  let container: HTMLDivElement;
  let svg: any;
  let simulation: any;
  
  // Graph data
  let nodes: GraphNode[] = [];
  let links: GraphLink[] = [];
  let clusters: Map<string, number> = new Map();
  
  // Visualization settings
  let colorScheme = d3.schemeTableau10;
  let width = 1200;
  let height = 700;
  
  // Zoom behavior
  let zoom: d3.ZoomBehavior<SVGSVGElement, unknown>;

  function updateSize() {
    if (!container || !svg) return;
    const rect = container.getBoundingClientRect();
    width = Math.max(320, Math.floor(rect.width));
    // keep height stable but ensure at least 400
    height = Math.max(400, height);
    svg
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height]);
  }

  function handleResize() {
    updateSize();
    if (simulation) {
      simulation
        .force('center', d3.forceCenter(width / 2, height / 2))
        .alpha(0.2)
        .restart();
    }
  }

  let stopResize: (() => void) | null = null;

  onMount(() => {
    initializeGraph();
    updateSize();
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', handleResize);
      stopResize = () => window.removeEventListener('resize', handleResize);
    }
  });

  if (typeof window !== 'undefined') {
    onDestroy(() => {
      if (simulation) {
        simulation.stop();
      }
      if (stopResize) stopResize();
    });
  }

  $: if (container && items.length > 0 && neighbors) {
    updateGraph();
  }

  $: if (svg && selectedId) {
    highlightSelection();
  }

  function initializeGraph() {
    // Create SVG
    svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])
      .attr('style', 'max-width: 100%; height: auto;');

    // Add zoom behavior
    zoom = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event: any) => {
        svg.select('.graph-container').attr('transform', event.transform);
      });

    svg.call(zoom);

    // Create container group
    svg.append('g').attr('class', 'graph-container');
  }

  function updateGraph() {
    if (!svg) return;

    // Build graph data
    const nodeSet = new Set<string>();
    const linkList: GraphLink[] = [];
    
    // Sample nodes if too many
    const itemsToShow = items.slice(0, maxNodes);
    
    itemsToShow.forEach(item => {
      nodeSet.add(item.id);
    });

    // Build links from neighbors data
    Object.entries(neighbors).forEach(([sourceId, neighborList]) => {
      if (!nodeSet.has(sourceId)) return;
      
      neighborList.forEach(neighbor => {
        if (nodeSet.has(neighbor.id) && neighbor.score >= minScore) {
          linkList.push({
            source: sourceId,
            target: neighbor.id,
            score: neighbor.score,
            S_text: neighbor.S_text,
            S_date: neighbor.S_date,
            S_place: neighbor.S_place
          });
        }
      });
    });

    // Create nodes array with metadata
    nodes = Array.from(nodeSet).map(id => {
      const item = items.find(i => i.id === id);
      return {
        id,
        title: Array.isArray(item?.title) ? item.title[0] : item?.title || id,
        year: item?.year,
        type: item?.type,
        collection: item?.collection,
        degree: 0, // will be calculated
        cluster: 0
      };
    });

    // Calculate degree for each node
    const degreeMap = new Map<string, number>();
    linkList.forEach(link => {
      const s = typeof link.source === 'string' ? link.source : link.source.id;
      const t = typeof link.target === 'string' ? link.target : link.target.id;
      degreeMap.set(s, (degreeMap.get(s) || 0) + 1);
      degreeMap.set(t, (degreeMap.get(t) || 0) + 1);
    });
    
    nodes.forEach(node => {
      node.degree = degreeMap.get(node.id) || 0;
    });

    links = linkList;

    // Detect communities using simple algorithm
    detectCommunities();

    // Render the graph
    renderGraph();
  }

  function detectCommunities() {
    // Community detection using Weighted Label Propagation Algorithm (LPA)

    // 1) Build weighted adjacency map from current links
    const adjacency = new Map<string, Map<string, number>>();
    links.forEach(link => {
      const s = typeof link.source === 'string' ? link.source : link.source.id;
      const t = typeof link.target === 'string' ? link.target : link.target.id;
      const w = Number.isFinite(link.score) ? link.score : 1;
      if (!adjacency.has(s)) adjacency.set(s, new Map());
      if (!adjacency.has(t)) adjacency.set(t, new Map());
      adjacency.get(s)!.set(t, (adjacency.get(s)!.get(t) || 0) + w);
      adjacency.get(t)!.set(s, (adjacency.get(t)!.get(s) || 0) + w);
    });

    // 2) Run label propagation
    const labels = labelPropagation(adjacency, 40);

    // 3) Map arbitrary labels to compact cluster indices 0..k-1
    clusters.clear();
    const labelToCluster = new Map<string, number>();
    let nextCluster = 0;
    for (const n of nodes) {
      const lab = labels.get(n.id) || n.id;
      if (!labelToCluster.has(lab)) labelToCluster.set(lab, nextCluster++);
      clusters.set(n.id, labelToCluster.get(lab)!);
    }

    // 4) Assign cluster to nodes
    nodes.forEach(node => {
      node.cluster = clusters.get(node.id) || 0;
    });
  }

  // Weighted Label Propagation Algorithm (Raghavan et al., 2007)
  function labelPropagation(
    adjacency: Map<string, Map<string, number>>,
    maxIter: number = 30
  ): Map<string, string> {
    const labels = new Map<string, string>();
    const nodeIds = nodes.map(n => n.id);

    // init label of each node to itself
    for (const id of nodeIds) labels.set(id, id);

    for (let iter = 0; iter < maxIter; iter++) {
      let changes = 0;

      // randomize processing order to avoid bias
      const order = nodeIds.slice();
      for (let i = order.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [order[i], order[j]] = [order[j], order[i]];
      }

      for (const u of order) {
        const neigh = adjacency.get(u);
        if (!neigh || neigh.size === 0) continue;

        // accumulate weight by neighbor labels
        const weightByLabel = new Map<string, number>();
        neigh.forEach((w, v) => {
          const lab = labels.get(v) || v;
          weightByLabel.set(lab, (weightByLabel.get(lab) || 0) + w);
        });

        // select label with maximal total weight (tie-break by stable string order)
        let bestLabel = labels.get(u) || u;
        let bestScore = -Infinity;
        weightByLabel.forEach((sum, lab) => {
          if (sum > bestScore || (sum === bestScore && lab < bestLabel)) {
            bestScore = sum;
            bestLabel = lab;
          }
        });

        if (bestLabel !== labels.get(u)) {
          labels.set(u, bestLabel);
          changes++;
        }
      }

      if (changes === 0) break; // converged
    }

    return labels;
  }

  function renderGraph() {
    const g = svg.select('.graph-container');
    g.selectAll('*').remove();

    // Create link elements
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', (d: GraphLink) => 0.2 + d.score * 0.6)
      .attr('stroke-width', (d: GraphLink) => Math.max(0.5, d.score * 3));

    // Create node elements
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(drag(simulation) as any);

    // Add circles to nodes
    node.append('circle')
      .attr('r', (d: GraphNode) => Math.max(3, Math.min(15, 3 + Math.sqrt(d.degree))))
      .attr('fill', (d: GraphNode) => colorScheme[d.cluster % colorScheme.length])
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .on('click', (event: any, d: GraphNode) => {
        event.stopPropagation();
        onNodeClick(d.id);
      })
      .on('mouseover', function(this: SVGCircleElement, event: any, d: GraphNode) {
        d3.select(this).attr('stroke', '#000').attr('stroke-width', 2);
        try { onNodeHover(d.id); } catch {}
        
        // Show tooltip
        const tooltip = g.append('g')
          .attr('class', 'tooltip')
          .attr('transform', `translate(${d.x},${d.y})`);
        
        const text = tooltip.append('text')
          .attr('dy', -20)
          .attr('text-anchor', 'middle')
          .style('font-size', '12px')
          .style('font-weight', 'bold')
          .style('fill', '#000')
          .style('pointer-events', 'none');
        
        text.append('tspan')
          .text(d.title.substring(0, 50) + (d.title.length > 50 ? '...' : ''));
        
        const bbox = (text.node() as any).getBBox();
        tooltip.insert('rect', 'text')
          .attr('x', bbox.x - 4)
          .attr('y', bbox.y - 2)
          .attr('width', bbox.width + 8)
          .attr('height', bbox.height + 4)
          .attr('fill', 'white')
          .attr('stroke', '#000')
          .attr('rx', 3);
      })
      .on('mouseout', function(this: SVGCircleElement) {
        d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
        g.selectAll('.tooltip').remove();
        try { onNodeHover(null); } catch {}
      });

    // Add labels for high-degree nodes
    node.filter((d: GraphNode) => d.degree > 5)
      .append('text')
      .attr('dx', 8)
      .attr('dy', 3)
      .style('font-size', '8px')
      .style('fill', '#333')
      .style('pointer-events', 'none')
      .text((d: GraphNode) => d.title.substring(0, 20));

    // Create force simulation
    simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links)
        .id((d: any) => d.id)
        .distance((d: any) => 100 - d.score * 50)
        .strength((d: any) => d.score))
      .force('charge', d3.forceManyBody()
        .strength(-30)
        .distanceMax(200))
      .force('cluster', forceCluster())
      .force('collision', d3.forceCollide()
        .radius((d: any) => Math.max(3, Math.min(15, 3 + Math.sqrt(d.degree))) + 2))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .on('tick', ticked);

    function ticked() {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    }
  }

  // Custom force to cluster nodes by community
  function forceCluster() {
    let nodes: GraphNode[];
    const strength = 0.3;
    const centerX = width / 2;
    const centerY = height / 2;

    function force(alpha: number) {
      // Calculate cluster centers
      const clusterCenters = new Map<number, { x: number; y: number; count: number }>();
      
      nodes.forEach(node => {
        if (!clusterCenters.has(node.cluster)) {
          const angle = (node.cluster / 10) * 2 * Math.PI;
          const radius = 200;
          clusterCenters.set(node.cluster, {
            x: centerX + Math.cos(angle) * radius,
            y: centerY + Math.sin(angle) * radius,
            count: 0
          });
        }
      });

      // Apply force towards cluster center
      nodes.forEach(node => {
        const center = clusterCenters.get(node.cluster);
        if (center && node.x !== undefined && node.y !== undefined) {
          node.vx = (node.vx || 0) + (center.x - node.x) * strength * alpha;
          node.vy = (node.vy || 0) + (center.y - node.y) * strength * alpha;
        }
      });
    }

    force.initialize = function(_: GraphNode[]) {
      nodes = _;
    };

    return force;
  }

  function drag(simulation: d3.Simulation<any, any>) {
    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended);
  }

  function highlightSelection() {
    if (!svg || !selectedId) return;

    svg.select('.nodes').selectAll('circle')
      .attr('stroke', (d: any) => d.id === selectedId ? '#ff0000' : '#fff')
      .attr('stroke-width', (d: any) => d.id === selectedId ? 3 : 1.5);

    // Highlight connected links
    svg.select('.links').selectAll('line')
      .attr('stroke', (d: any) => 
        d.source.id === selectedId || d.target.id === selectedId ? '#ff6b6b' : '#999')
      .attr('stroke-opacity', (d: any) => 
        d.source.id === selectedId || d.target.id === selectedId ? 0.8 : 0.2 + d.score * 0.6);
  }

  export function resetZoom() {
    if (svg && zoom) {
      svg.transition()
        .duration(750)
        .call(zoom.transform as any, d3.zoomIdentity);
    }
  }

  export function reheat() {
    if (simulation) {
      simulation.alpha(1).restart();
    }
  }
</script>

<div bind:this={container} class="network-container w-full h-full bg-gray-50 rounded-lg border border-gray-200"></div>

<style>
  .network-container {
    min-height: 600px;
  }
</style>
