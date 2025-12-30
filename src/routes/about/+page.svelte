<script lang="ts">
    /**
     * @fileoverview About page for the Graphical Archive project.
     * This page provides information on how to read and navigate the archive.
     * 
     * @requires svelte
     * @requires $lib/components/NetworkGraph.svelte
     * @requires $lib/components/InfoPanel.svelte
     * 
     * @author Jairo Melo-Florez
     * @version 1.0.0
     */
    
    import { onMount } from 'svelte';
    import { browser } from '$app/environment';
    import nodeImage from '$lib/assets/imgs/node.png';
    import katex from 'katex';
    import 'katex/dist/katex.min.css';
    import bibtexParse from 'bibtex-parse';
    import NetworkGraph from '$lib/NetworkGraph.svelte';
    import { items, edges } from '$lib/stores';
    
    export let data;

    let vectorMatrix: HTMLElement;
    
    const matrixLatex = '\\begin{bmatrix} \\vec{\\text{metadata}} \\parallel \\vec{\\text{spatial}} \\parallel \\vec{\\text{temporal}} \\parallel \\vec{\\text{interaction}} \\end{bmatrix}';

    // Interactive graph state
    let selectedNode: any = null;
    let selectedEdge: { source: any; target: any; scores: any } | null = null;
    let neighbors: Record<string, any[]> = {};
    let edgesMap: Map<string, any> = new Map();

    // Normalize neighbors data and build edges map
    function normalizeNeighbors(n: any) {
        if (Array.isArray(n)) return n;
        if (Array.isArray(n?.pairs)) {
            return n.pairs.map((p: any) => ({ source: p.a, target: p.b, score: p.score }));
        }
        return n?.graph?.edges ?? [];
    }

    function handleNodeClick(id: string) {
        selectedNode = $items.find(item => item.id === id);
        selectedEdge = null; // Clear edge selection when clicking a node
    }

    function handleEdgeClick(sourceId: string, targetId: string) {
        const sourceItem = $items.find(item => item.id === sourceId);
        const targetItem = $items.find(item => item.id === targetId);
        
        if (!sourceItem || !targetItem) return;
        
        // Find edge data from neighbors
        const sourceNeighbors = data.neighbors[sourceId] || [];
        const targetNeighbors = data.neighbors[targetId] || [];
        
        let edgeData = sourceNeighbors.find((n: any) => n.id === targetId);
        if (!edgeData) {
            edgeData = targetNeighbors.find((n: any) => n.id === sourceId);
        }
        
        if (edgeData) {
            selectedEdge = {
                source: sourceItem,
                target: targetItem,
                scores: edgeData
            };
            selectedNode = null; // Clear node selection when clicking an edge
        }
    }

    // BibTeX references
    let references: Record<string, any> = {};
    let citationKeys: string[] = [];
    let referencesLoaded = false;

    async function loadReferences() {
        try {
            const response = await fetch('/references.bib');
            const bibText = await response.text();
            console.log('BibTeX loaded:', bibText.substring(0, 200));
            
            const parsed = bibtexParse.parse(bibText);
            console.log('Parsed entries:', parsed);
            
            // bibtex-parse returns an array directly
            if (parsed && Array.isArray(parsed)) {
                parsed.forEach((item: any) => {
                    if (item.itemtype === 'entry') {
                        // Convert fields array to object for easier access
                        const fieldsObj: any = {};
                        item.fields.forEach((field: any) => {
                            fieldsObj[field.name] = field.value;
                        });
                        
                        references[item.key] = {
                            type: item.type,
                            key: item.key,
                            fields: fieldsObj
                        };
                        console.log('Processed entry:', item.key);
                    }
                });
            }
            
            // Track citations used in the text
            citationKeys = ['huiExistenceDigitalObjects2016'];
            referencesLoaded = true;
            console.log('References loaded:', Object.keys(references));
        } catch (error) {
            console.error('Error loading references:', error);
        }
    }

    function formatAuthors(authors: string): string {
        if (!authors) return '';
        const authorList = authors.split(' and ');
        if (authorList.length === 1) return authorList[0];
        if (authorList.length === 2) return `${authorList[0]} and ${authorList[1]}`;
        return `${authorList[0]} et al.`;
    }

    function formatReference(entry: any): string {
        const author = formatAuthors(entry.fields.author);
        const year = entry.fields.year;
        const title = entry.fields.title?.replace(/[{}]/g, '');
        const publisher = entry.fields.publisher;
        const journal = entry.fields.journal;
        
        if (entry.type === 'book') {
            return `${author} (${year}). <em>${title}</em>. ${publisher}.`;
        } else if (entry.type === 'article') {
            const volume = entry.fields.volume ? ` ${entry.fields.volume}` : '';
            const number = entry.fields.number ? `(${entry.fields.number})` : '';
            const pages = entry.fields.pages ? `, ${entry.fields.pages}` : '';
            return `${author} (${year}). ${title}. <em>${journal}</em>${volume}${number}${pages}.`;
        }
        return `${author} (${year}). ${title}.`;
    }

    onMount(() => {
        // Load graph data
        items.set(data.metadata || []);
        edges.set(normalizeNeighbors(data.neighbors));
        
        // Build neighbors object for NetworkGraph
        neighbors = data.neighbors || {};
        
        if (vectorMatrix) {
            katex.render(matrixLatex, vectorMatrix, {
                throwOnError: false,
                displayMode: true
            });
        }
        
        loadReferences();
    });

</script>

<svelte:head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" integrity="sha384-n8MVd4RsNIU0tAv4ct0nTaAbDJwPJzDEaqSD1odI+WdtXRGWt2kTvGFasHpSy3SV" crossorigin="anonymous">
</svelte:head>

<article class="about-page">
    <h1>How to read the Graphical Archive</h1>

    <p>
        The Graphical Archive is a conceptualization of archival topology through relational proximity, moving beyond traditional hierarchies toward network-based navigation. This is not a functional platform but rather an exploration of how archives can be visualized and interacted with in a non-linear fashion.
    </p>

    <h2>Nodes and Edges</h2>

    <h3>Understanding Nodes</h3>

    <p>
        We are representing each archival item as a <strong>node</strong> in a network graph. The complexity of the archival node is totally arbitrary, and can be understood as a "digital object" in the terms of Yuk Hui, that is: "objects that take shape on a screen or hide in the back end of a computer program, composed of data and metadata regulated by structures or schemas." <a href="#ref-huiExistenceDigitalObjects2016" class="citation"><sup>1</sup></a>
    </p>

    <p>
        The visualization below shows a sample of 50 nodes from the archive, each representing a record. <strong>Click on any node</strong> to explore its complete metadata structure—this reveals what information each digital object carries:
    </p>

    <div class="graph-container">
        <NetworkGraph 
            items={$items.slice(0, 50)} 
            neighbors={{}} 
            onNodeClick={handleNodeClick}
            maxNodes={50}
            minScore={0.02}
        />
    </div>

    {#if selectedNode}
        <div class="selected-node-info">
            <h4>Selected Node: {Array.isArray(selectedNode.title) ? selectedNode.title[0] : selectedNode.title}</h4>
            <pre><code class="language-json">{JSON.stringify(selectedNode, null, 2)}</code></pre>
        </div>
    {:else}
        <p class="instruction">Click on a node in the graph above to see its complete JSON structure.</p>
    {/if}

    <p>
        The node is an abstraction, a capsule, that contains all the relevant metadata and the connections to the digital artifact itself (e.g., the link to the Europeana record, the IIIF manifest, etc.).
    </p>

    <h3>Connecting Through Edges</h3>

    <p>
        To avoid orphan nodes, every object must be connected to at least one other object through <strong>edges</strong>. Edges represent variable-strength relationships between nodes based on shared attributes. The proximity, or neighborness, of nodes is determined by a weighted score combining three similarity vectors:
    </p>

    <div class="vectors-matrix" bind:this={vectorMatrix}></div>

    <p>
        Each vector can be weighted differently based on user preferences, allowing for a dynamic exploration of the archive based on different relational criteria. The current implementation uses: <strong>60% textual similarity</strong>, <strong>20% temporal proximity</strong>, and <strong>20% spatial proximity</strong>.
    </p>

    <p>
        Now let's see how these edges connect nodes in practice. The visualization below shows the same 50 nodes, but this time with their relationships visible as connecting lines. The nodes are colored according to their <strong>community clusters</strong>, which are automatically detected using a label propagation algorithm. Unlike traditional archival hierarchies based on collections or provenance, these clusters emerge organically from the relational structure of the network itself. <strong>Click on any edge</strong> (connection line) to see its detailed similarity breakdown:
    </p>

    <div class="graph-container">
        <NetworkGraph 
            items={$items.slice(0, 50)} 
            neighbors={neighbors} 
            onNodeClick={handleNodeClick}
            onEdgeClick={handleEdgeClick}
            maxNodes={50}
            minScore={0.02}
        />
    </div>

    {#if selectedEdge}
        <div class="selected-edge-info">
            <h4>Edge Relationship</h4>
            <div class="edge-nodes">
                <div class="edge-node">
                    <strong>Source:</strong> {Array.isArray(selectedEdge.source.title) ? selectedEdge.source.title[0] : selectedEdge.source.title}
                </div>
                <div class="edge-connector">↔</div>
                <div class="edge-node">
                    <strong>Target:</strong> {Array.isArray(selectedEdge.target.title) ? selectedEdge.target.title[0] : selectedEdge.target.title}
                </div>
            </div>
            <div class="similarity-scores">
                <h5>Similarity Breakdown</h5>
                <div class="score-grid">
                    <div class="score-item">
                        <span class="score-label">Combined Score:</span>
                        <span class="score-value main">{(selectedEdge.scores.score * 100).toFixed(1)}%</span>
                    </div>
                    <div class="score-item">
                        <span class="score-label">Textual Similarity:</span>
                        <span class="score-value">{(selectedEdge.scores.S_text * 100).toFixed(1)}%</span>
                    </div>
                    <div class="score-item">
                        <span class="score-label">Temporal Proximity:</span>
                        <span class="score-value">{(selectedEdge.scores.S_date * 100).toFixed(1)}%</span>
                    </div>
                    <div class="score-item">
                        <span class="score-label">Spatial Proximity:</span>
                        <span class="score-value">{(selectedEdge.scores.S_place * 100).toFixed(1)}%</span>
                    </div>
                </div>
                <p class="score-explanation">
                    This edge represents a weighted combination of the three similarity vectors. The combined score is calculated as:
                    <em>0.6 × Textual + 0.2 × Temporal + 0.2 × Spatial</em>
                </p>
            </div>
        </div>
    {:else}
        <p class="instruction">Click on an edge (connection line) in the graph above to see the detailed similarity breakdown between two nodes.</p>
    {/if}

    <p>
        This is a different approach compared to filtering or faceting mechanisms commonly used in digital archives, where the connections are pre-defined and static. Here, the relationships are fluid and can be adjusted in real-time. Records might cluster across different collections if they share strong similarities in their attributes.
    </p>

    <h2>Navigating the Archive</h2>
    <p>
        This is a different approach compared to filtering or faceting mechanisms commonly used in digital archives, where the connections are pre-defined and static. Here, the relationships are fluid and can be adjusted in real-time.
    </p>

    <h2>Navigating the Archive</h2>

    <p>
        An interface is a way to represent data in a human-readable format. In our interface, the archive is represented through three main components:
    </p>

    <h3>Network Graph</h3>

    <p>
        This is the most abstract layer of this interface. This is a graphical interpretation of the <em>middleware</em> that connects all items in the archive based on their relationships. Each node represents an item, and edges represent relationships between them. Nodes are closer together based on stronger relationships, determined by the weight of each attribute.
    </p>

    <h3>Search and Filter</h3>

    <p>
        This panel represents the traditional way of navigating an archive. The exploration of the archive is done through a search box, and the results can be narrowed down using filters such as language and dates. The results here are represented both in the network graph and in the info panel.
    </p>

    <h3>Details</h3>

    <p>
        This panel shows the selected item with some detail. It shows the thumbnail for the artifact, its title, year, language, country, and the collection it belongs to. It also provides links to the Europeana record. The selected item is accompanied by its nearest neighbors, showing the closest related items based on the current weight configuration. It also indicates how much the user interaction is affecting the relationships by making some elements closer to the selected item.
    </p>

    <h2>References</h2>

    <div class="references">
        {#if referencesLoaded}
            {#each citationKeys as key, index}
                {#if references[key]}
                    <div class="reference-item" id="ref-{key}">
                        <span class="reference-number">[{index + 1}]</span>
                        <span class="reference-content">
                            {@html formatReference(references[key])}
                        </span>
                    </div>
                {:else}
                    <p>Reference key "{key}" not found in bibliography.</p>
                {/if}
            {/each}
        {:else}
            <p>Loading references...</p>
        {/if}
    </div>
</article>

<style>
    .about-page {
        max-width: 800px;
        margin: 0 auto;
        padding: 2rem;
        line-height: 1.6;
    }

    h1 {
        font-size: 2.5rem;
        margin-bottom: 1.5rem;
        font-weight: 700;
    }

    h2 {
        font-size: 2rem;
        margin-top: 3rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }

    h3 {
        font-size: 1.5rem;
        margin-top: 2rem;
        margin-bottom: 0.75rem;
        font-weight: 600;
    }

    p {
        margin-bottom: 1rem;
    }

    img {
        max-width: 100%;
        height: auto;
        margin: 2rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    pre {
        background-color: #f5f5f5;
        padding: 1.5rem;
        border-radius: 8px;
        overflow-x: auto;
        margin: 1.5rem 0;
    }

    code {
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.9rem;
    }

    .vectors-matrix {
        margin: 2rem 0;
        text-align: center;
        font-size: 1.2rem;
        overflow-x: auto;
    }

    .graph-container {
        width: 100%;
        height: 500px;
        margin: 2rem 0;
        border: 1px solid #ddd;
        border-radius: 8px;
        overflow: hidden;
    }

    .selected-node-info {
        margin: 2rem 0;
    }

    .selected-node-info h4 {
        font-size: 1.25rem;
        margin-bottom: 1rem;
        color: #333;
    }

    .instruction {
        text-align: center;
        color: #666;
        font-style: italic;
        padding: 2rem;
        background-color: #f9f9f9;
        border-radius: 8px;
        margin: 2rem 0;
    }

    .selected-edge-info {
        margin: 2rem 0;
        padding: 1.5rem;
        background-color: #f9f9f9;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
    }

    .selected-edge-info h4 {
        font-size: 1.5rem;
        margin-bottom: 1.5rem;
        color: #333;
    }

    .edge-nodes {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background-color: white;
        border-radius: 6px;
    }

    .edge-node {
        flex: 1;
        padding: 0.5rem;
    }

    .edge-connector {
        font-size: 2rem;
        color: #0066cc;
        font-weight: bold;
    }

    .similarity-scores {
        background-color: white;
        padding: 1.5rem;
        border-radius: 6px;
    }

    .similarity-scores h5 {
        font-size: 1.2rem;
        margin-bottom: 1rem;
        color: #333;
    }

    .score-grid {
        display: grid;
        gap: 1rem;
        margin-bottom: 1rem;
    }

    .score-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem;
        background-color: #f5f5f5;
        border-radius: 4px;
    }

    .score-label {
        font-weight: 500;
        color: #555;
    }

    .score-value {
        font-weight: 600;
        color: #0066cc;
        font-size: 1.1rem;
    }

    .score-value.main {
        font-size: 1.3rem;
        color: #004499;
    }

    .score-explanation {
        margin-top: 1rem;
        padding: 1rem;
        background-color: #f9f9f9;
        border-radius: 4px;
        font-size: 0.9rem;
        color: #666;
        line-height: 1.6;
    }

    .score-explanation em {
        font-style: italic;
        color: #0066cc;
        font-weight: 600;
    }

    sup {
        font-size: 0.75rem;
        vertical-align: super;
    }

    .citation {
        text-decoration: none;
        color: #0066cc;
        font-weight: 600;
    }

    .citation:hover {
        text-decoration: underline;
    }

    .references {
        margin-top: 2rem;
        padding-top: 2rem;
        border-top: 2px solid #e0e0e0;
    }

    .reference-item {
        margin-bottom: 1rem;
        display: flex;
        gap: 0.5rem;
        line-height: 1.6;
    }

    .reference-number {
        font-weight: 600;
        color: #666;
        flex-shrink: 0;
    }

    .reference-content {
        flex: 1;
    }

    .reference-content :global(em) {
        font-style: italic;
    }
</style>