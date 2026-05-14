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
    
    import { asset } from '$app/paths';

    export let data;

    let vectorMatrix: HTMLElement;
    let formulaStextRef: HTMLElement;
    let formulaSdateRef: HTMLElement;
    let formulaSdateDetail: HTMLElement;
    let formulaSpaceDetail: HTMLElement;
    let formulaSuserDetail: HTMLElement;
    let formulaGMain: HTMLElement;
    let formulaGMainDetail: HTMLElement;
    let formulaGDynamic: HTMLElement;
    let formulaGExample: HTMLElement;
    
    const matrixLatex = '\\begin{bmatrix} \\vec{\\text{metadata}} \\parallel \\vec{\\text{spatial}} \\parallel \\vec{\\text{temporal}} \\parallel \\vec{\\text{interaction}} \\end{bmatrix}';
    const formulaStextLatex = 'S_{\\text{text}}(i, j) = \\text{cosine\\_similarity}(\\text{TF-IDF}_i, \\text{TF-IDF}_j)';
    const formulaSdateLatex = 'S_{\\text{date}}(i, j) = \\exp\\left(-\\frac{\\text{distance}(i, j)}{25}\\right)';
    const formulaSdateDetailLatex = '\\text{where distance}(i, j) = \\text{min\\_distance\\_between\\_ranges}(\\text{item}_i, \\text{item}_j), \\quad \\text{distance} = 0 \\text{ if ranges overlap}';
    const formulaSpaceLatex = 'S_{\\text{place}}(i, j) = \\exp\\left(-\\frac{\\text{distance}_{\\text{km}}(i, j)}{400}\\right)';
    const formulaSpaceDetailLatex = '\\text{where distance}_{\\text{km}}(i, j) = \\text{haversine}(\\text{lat}_i, \\text{lon}_i, \\text{lat}_j, \\text{lon}_j)';
    const formulaSuserLatex = 'S_{\\text{user}}(i, j) = 0.4 \\times \\text{co-view}_{\\text{normalized}}(i, j) + 0.6 \\times \\text{co-bookmark}_{\\text{normalized}}(i, j)';
    const formulaGMainLatex = 'G_{ij} = \\alpha \\times S_{\\text{text}}(i, j) + \\beta \\times S_{\\text{date}}(i, j) + \\gamma \\times S_{\\text{place}}(i, j) + \\delta \\times S_{\\text{user}}(i, j)';
    const formulaGMainDetailLatex = '\\text{where } \\alpha + \\beta + \\gamma + \\delta = 1.0';
    const formulaGExampleLatex = 'G_{ij} = \\frac{75}{190} \\times S_{\\text{text}}(i, j) + \\frac{45}{190} \\times S_{\\text{date}}(i, j) + \\frac{55}{190} \\times S_{\\text{place}}(i, j) + \\frac{15}{190} \\times S_{\\text{user}}(i, j)';

    // Interactive graph state
    let selectedNode: any = null;
    let selectedEdge: { source: any; target: any; scores: any } | null = null;
    let expandedSimilarity: 'text' | 'date' | 'place' | null = null;
    let neighbors: Record<string, any[]> = {};
    let filteredNeighbors: Record<string, any[]> = {};
    let edgesMap: Map<string, any> = new Map();
    let gazetteer: Record<string, any[]> = {};

    // Interactive demo state
    let demoSelectedItem: any = null;
    let demoClickedItems: Set<string> = new Set();
    let demoWeights = { text: 50, date: 20, place: 20, user: 10 };
    let demoRecommendations: any[] = [];
    let demoAllRecommendations: any[] = [];
    let demoDisplayCount: number = 15;
    let initialPositions: Map<string, number> = new Map();

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
            expandedSimilarity = null; // Reset expanded view
        }
    }

    function toggleSimilarityDetail(type: 'text' | 'date' | 'place') {
        expandedSimilarity = expandedSimilarity === type ? null : type;
    }

    function formatArrayField(field: any): string {
        if (Array.isArray(field)) return field.join(', ');
        return field || 'N/A';
    }

    function getCoordinates(item: any): { lat: number; lon: number } | null {
        // First try item's own coordinates
        if (item.place_lat && item.place_lon) {
            return { lat: item.place_lat, lon: item.place_lon };
        }
        
        // Fallback to gazetteer using place_label
        if (item.place_label && data.gazetteer) {
            const placeLabel = Array.isArray(item.place_label) 
                ? item.place_label[0] 
                : item.place_label;
            
            const gazetteerEntry = data.gazetteer[placeLabel];
            if (gazetteerEntry && gazetteerEntry.place_lat && gazetteerEntry.place_lon) {
                return { 
                    lat: gazetteerEntry.place_lat, 
                    lon: gazetteerEntry.place_lon 
                };
            }
        }
        
        return null;
    }

    // Demo functions
    function initializeDemo() {
        // Pick a random starting item
        const itemsArray = $items.filter(item => 
            item.thumbnail && 
            data.neighbors[item.id] && 
            data.neighbors[item.id].length >= 20
        );
        if (itemsArray.length > 0) {
            const randomIndex = Math.floor(Math.random() * Math.min(itemsArray.length, 50));
            demoSelectedItem = itemsArray[randomIndex];
            updateDemoRecommendations();
        }
    }

    function calculateUserSimilarity(itemId: string): number {
        if (demoClickedItems.size === 0) return 0;
        
        // Simple co-occurrence: if item was clicked, high score
        if (demoClickedItems.has(itemId)) return 1.0;
        
        // If item shares neighbors with clicked items, medium score
        const itemNeighbors = new Set(
            (data.neighbors[itemId] || []).map((n: any) => n.id)
        );
        
        let sharedCount = 0;
        demoClickedItems.forEach(clickedId => {
            if (itemNeighbors.has(clickedId)) sharedCount++;
        });
        
        return sharedCount > 0 ? 0.3 + (sharedCount * 0.2) : 0;
    }

    function updateDemoRecommendations() {
        if (!demoSelectedItem) return;
        
        const baseNeighbors = data.neighbors[demoSelectedItem.id] || [];
        
        // Normalize weights to sum to 1.0 for proper mathematical calculation
        const sum = demoWeights.text + demoWeights.date + demoWeights.place + demoWeights.user;
        const w_text = sum > 0 ? demoWeights.text / sum : 0;
        const w_date = sum > 0 ? demoWeights.date / sum : 0;
        const w_place = sum > 0 ? demoWeights.place / sum : 0;
        const w_user = sum > 0 ? demoWeights.user / sum : 0;
        
        // Recalculate scores with normalized weights
        const scoredNeighbors = baseNeighbors.map((neighbor: any) => {
            const userScore = calculateUserSimilarity(neighbor.id);
            const weightedScore = 
                w_text * neighbor.S_text +
                w_date * neighbor.S_date +
                w_place * neighbor.S_place +
                w_user * userScore;
            
            return {
                ...neighbor,
                weightedScore,
                userScore,
                item: $items.find(i => i.id === neighbor.id)
            };
        });
        
        // Sort by weighted score and store all
        demoAllRecommendations = scoredNeighbors
            .filter((n: any) => n.item)
            .sort((a: any, b: any) => b.weightedScore - a.weightedScore);
        
        // Take the top N based on display count
        demoRecommendations = demoAllRecommendations.slice(0, demoDisplayCount);
        
        // Store initial positions if this is the first recommendation
        if (initialPositions.size === 0 && demoAllRecommendations.length > 0) {
            demoAllRecommendations.forEach((rec, index) => {
                initialPositions.set(rec.id, index + 1);
            });
        }
    }

    function handleDemoItemClick(itemId: string) {
        // Track the click for user interactions
        demoClickedItems.add(itemId);
        demoClickedItems = demoClickedItems;
        
        // Make the clicked item the new selected item (like clicking a YouTube recommendation)
        const clickedItem = $items.find(i => i.id === itemId);
        if (clickedItem) {
            demoSelectedItem = clickedItem;
        }
        
        // User interaction similarity (S_user) increases automatically for clicked items
        // but weights remain under your manual control
        updateDemoRecommendations();
    }

    function handleWeightChange() {
        // Just update recommendations - weights are already in percentage form (0-100)
        // They'll be used directly in the weighted score calculation
        updateDemoRecommendations();
    }

    function handleDisplayCountChange() {
        demoRecommendations = demoAllRecommendations.slice(0, demoDisplayCount);
    }

    function resetDemo() {
        demoClickedItems.clear();
        demoClickedItems = demoClickedItems;
        initialPositions.clear();
        initialPositions = initialPositions;
        demoWeights = { text: 50, date: 20, place: 20, user: 10 };
        initializeDemo();
    }

    function formatTitle(item: any): string {
        if (!item) return 'Unknown';
        if (Array.isArray(item.title)) return item.title[0] || 'Unknown';
        return item.title || 'Unknown';
    }

    // BibTeX references
    let references: Record<string, any> = {};
    let citationKeys: string[] = [];
    let referencesLoaded = false;

    async function loadReferences() {
        try {
            const response = await fetch(asset('/references.bib'));
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
        
        // Create filtered version with only top 10 neighbors for visualization
        // This prevents over-dense networks while keeping all 50 for the demo
        filteredNeighbors = Object.fromEntries(
            Object.entries(neighbors).map(([key, neighborList]) => [
                key,
                neighborList
                    .sort((a: any, b: any) => b.score - a.score)
                    .slice(0, 10)
            ])
        );
        
        if (vectorMatrix) {
            katex.render(matrixLatex, vectorMatrix, {
                throwOnError: false,
                displayMode: true
            });
        }
        
        // Render all LaTeX formulas
        if (formulaStextRef) katex.render(formulaStextLatex, formulaStextRef, { throwOnError: false });
        if (formulaSdateRef) katex.render(formulaSdateLatex, formulaSdateRef, { throwOnError: false });
        if (formulaSdateDetail) katex.render(formulaSdateDetailLatex, formulaSdateDetail, { throwOnError: false });
        if (formulaSpaceDetail) katex.render(formulaSpaceLatex + ', \\quad ' + formulaSpaceDetailLatex, formulaSpaceDetail, { throwOnError: false });
        if (formulaSuserDetail) katex.render(formulaSuserLatex, formulaSuserDetail, { throwOnError: false });
        if (formulaGMain) katex.render(formulaGMainLatex, formulaGMain, { throwOnError: false, displayMode: true });
        if (formulaGMainDetail) katex.render(formulaGMainDetailLatex, formulaGMainDetail, { throwOnError: false, displayMode: true });
        if (formulaGDynamic) katex.render(formulaGMainLatex, formulaGDynamic, { throwOnError: false, displayMode: true });
        if (formulaGExample) katex.render(formulaGExampleLatex, formulaGExample, { throwOnError: false });
        
        loadReferences();
        initializeDemo();
    });

</script>

<svelte:head>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css" integrity="sha384-n8MVd4RsNIU0tAv4ct0nTaAbDJwPJzDEaqSD1odI+WdtXRGWt2kTvGFasHpSy3SV" crossorigin="anonymous">
</svelte:head>

<article class="about-page">
    <div class="text-body">
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
        Each vector can be weighted differently based on user preferences, allowing for a dynamic exploration of the archive based on different relational criteria. The pre-computed weights reserve space for user interactions: <strong>50% textual similarity</strong>, <strong>20% temporal proximity</strong>, <strong>20% spatial proximity</strong>, and <strong>10% user interaction</strong> (initially zero, grows with browsing behavior).
    </p>

    <div class="methodology-callouts">
        <details class="methodology-detail">
            <summary>
                <strong>Textual Similarity Calculation</strong>
                <span class="expand-icon">▶</span>
            </summary>
            <div class="detail-content">
                <p>
                    We calculate textual similarity using <a href="https://en.wikipedia.org/wiki/Tf%E2%80%93idf" target="_blank" rel="noopener">TF-IDF (Term Frequency-Inverse Document Frequency)</a> vectorization followed by cosine similarity measurement.
                </p>
                <p><strong>Fields used:</strong></p>
                <ul>
                    <li><code>title</code> — The item's title</li>
                    <li><code>concepts</code> — Subject headings and thematic tags</li>
                    <li><code>description</code> — Full text description of the item</li>
                    <li><code>place_label</code> — Textual place names (e.g., "Paris", "Dublin")</li>
                </ul>
                <p>
                    These four text fields are concatenated into a single document per item. TF-IDF assigns weights to words based on their frequency within each document and rarity across all documents, emphasizing distinctive terms. The cosine similarity between two TF-IDF vectors measures how similar their textual content is, ranging from 0 (completely different) to 1 (identical).
                </p>
                <p class="formula">
                    <span bind:this={formulaStextRef}></span>
                </p>
            </div>
        </details>

        <details class="methodology-detail">
            <summary>
                <strong>Temporal Proximity Calculation</strong>
                <span class="expand-icon">▶</span>
            </summary>
            <div class="detail-content">
                <p>
                    Temporal proximity measures how close two items are in time using an exponential decay kernel with range-awareness. This approach respects the temporal uncertainty inherent in archival records.
                </p>
                <p><strong>Fields used (priority order):</strong></p>
                <ul>
                    <li><code>year</code> — The primary year (used as exact point when available)</li>
                    <li><code>date_begin</code> and <code>date_end</code> — Date range boundaries (e.g., "1800-1850")</li>
                    <li>Single date fallbacks — Uses <code>date_begin</code> or <code>date_end</code> alone if only one is available</li>
                </ul>
                <p>
                    The algorithm first determines the temporal range for each item. If an exact <code>year</code> is specified, it's treated as a point in time. Otherwise, the range is constructed from <code>date_begin</code> and <code>date_end</code>. When comparing two items, the calculation finds the <strong>minimum distance between their temporal ranges</strong>.
                </p>
                <p class="note">
                    <strong>Key insight:</strong> Items with overlapping temporal ranges (e.g., 1800-1850 and 1840-1880) receive maximum temporal similarity, even if their midpoints differ. This better represents archival reality where dates are often uncertain or span multiple years.
                </p>
                <p>
                    The calculation uses a bandwidth of <strong>25 years</strong>, meaning items whose ranges are 25 years apart retain about 37% similarity (e<sup>-1</sup>), while items 50 years apart have about 14% similarity (e<sup>-2</sup>).
                </p>
                <p class="formula">
                    <span bind:this={formulaSdateRef}></span><br>
                    <span bind:this={formulaSdateDetail}></span>
                </p>
            </div>
        </details>

        <details class="methodology-detail">
            <summary>
                <strong>Spatial Proximity Calculation</strong>
                <span class="expand-icon">▶</span>
            </summary>
            <div class="detail-content">
                <p>
                    Spatial proximity is a <strong>geographical/geometrical measurement</strong>, not a textual comparison. It calculates the physical distance between two items' coordinates on Earth using the <a href="https://en.wikipedia.org/wiki/Haversine_formula" target="_blank" rel="noopener">Haversine formula</a>, then applies a Gaussian kernel to convert distance into similarity.
                </p>
                <p><strong>Fields used:</strong></p>
                <ul>
                    <li><code>place_lat</code> — Latitude coordinate</li>
                    <li><code>place_lon</code> — Longitude coordinate</li>
                </ul>
                <p>
                    The Haversine formula calculates the great-circle distance between two points on a sphere, accounting for Earth's curvature. This gives us the actual distance in kilometers between two locations.
                </p>
                <p class="note">
                    <strong>Coordinate enrichment:</strong> When coordinates are missing from the original metadata, we enrich them using a custom gazetteer that maps place names (like "Spain", "United States of America", "París") to their authoritative geographic coordinates from <a href="https://www.geonames.org/" target="_blank" rel="noopener">GeoNames</a>. This ensures spatial relationships can be calculated even when source data is incomplete.
                </p>
                <p>
                    A Gaussian kernel with a bandwidth of <strong>400 km</strong> transforms this distance into a similarity score. Items at the same location have maximum similarity (1.0), items 400 km apart retain about 37% similarity, and items 800 km apart have about 14% similarity.
                </p>
                <p class="note">
                    <strong>Important:</strong> While <code>place_label</code> (textual place names) and <code>country</code> appear in the metadata, they are <em>not used for spatial proximity</em>. Only the numerical coordinates determine this measurement. Place names do contribute to <em>textual similarity</em> instead.
                </p>
                <p class="formula">
                    <span bind:this={formulaSpaceDetail}></span>
                </p>
            </div>
        </details>

        <div class="final-formula">
            <strong>"Good Neighbor Index":</strong>
            <p class="formula-note">
                To calculate the "neighborness" between two archival items, we combine the four similarity vectors into a single weighted score <em>G<sub>ij</sub></em>:
            </p>
            <p class="formula main">
                <span bind:this={formulaGMain}></span><br>
                <span bind:this={formulaGMainDetail}></span>
            </p>
            <p class="formula-note">
                The weights (α, β, γ, δ) can be freely adjusted to explore different perspectives. The backend pre-computes neighbors using α=0.5, β=0.2, γ=0.2, δ=0.1 as default values, which allocate 50% to textual similarity, 20% to temporal proximity, 20% to spatial proximity, and 10% to user interactions. The user interaction component starts at S<sub>user</sub>=0 (no browsing data yet) and increases as visitors explore the archive. These weights can be dynamically adjusted through the interactive demo to emphasize different relational dimensions.
            </p>
        </div>
    </div>

    <p>
        Now let's see how these edges connect nodes in practice. The visualization below shows the same 50 nodes, but this time with their relationships visible as connecting lines. The nodes are colored according to their <strong>community clusters</strong>, which are automatically detected using a label propagation algorithm. Unlike traditional archival hierarchies based on collections or provenance, these clusters emerge organically from the relational structure of the network itself. <strong>Click on any edge</strong> (connection line) to see its detailed similarity breakdown:
    </p>

    <div class="graph-container">
        <NetworkGraph 
            items={$items.slice(0, 50)} 
            neighbors={filteredNeighbors} 
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
                    <div class="score-item clickable" role="button" tabindex="0" on:click={() => toggleSimilarityDetail('text')} on:keydown={(e) => e.key === 'Enter' && toggleSimilarityDetail('text')}>
                        <span class="score-label">Textual Similarity: <span class="hint">(click to see fields)</span></span>
                        <span class="score-value">{(selectedEdge.scores.S_text * 100).toFixed(1)}%</span>
                    </div>
                    <div class="score-item clickable" role="button" tabindex="0" on:click={() => toggleSimilarityDetail('date')} on:keydown={(e) => e.key === 'Enter' && toggleSimilarityDetail('date')}>
                        <span class="score-label">Temporal Proximity: <span class="hint">(click to see fields)</span></span>
                        <span class="score-value">{(selectedEdge.scores.S_date * 100).toFixed(1)}%</span>
                    </div>
                    <div class="score-item clickable" role="button" tabindex="0" on:click={() => toggleSimilarityDetail('place')} on:keydown={(e) => e.key === 'Enter' && toggleSimilarityDetail('place')}>
                        <span class="score-label">Spatial Proximity: <span class="hint">(click to see fields)</span></span>
                        <span class="score-value">{(selectedEdge.scores.S_place * 100).toFixed(1)}%</span>
                    </div>
                </div>
                
                {#if expandedSimilarity === 'text'}
                    <div class="metadata-comparison">
                        <h6>Textual Similarity Fields</h6>
                        <p class="comparison-note">Calculated using TF-IDF cosine similarity on combined text:</p>
                        <div class="comparison-grid">
                            <div class="comparison-column">
                                <strong>Source Node</strong>
                                <div class="field-group">
                                    <span class="field-label">Title:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.source.title)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Concepts:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.source.concepts)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Description:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.source.description)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Place Label:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.source.place_label)}</div>
                                </div>
                            </div>
                            <div class="comparison-column">
                                <strong>Target Node</strong>
                                <div class="field-group">
                                    <span class="field-label">Title:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.target.title)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Concepts:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.target.concepts)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Description:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.target.description)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Place Label:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.target.place_label)}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                {/if}
                
                {#if expandedSimilarity === 'date'}
                    <div class="metadata-comparison">
                        <h6>Temporal Proximity Fields</h6>
                        <p class="comparison-note">Calculated using exponential kernel on year difference (bandwidth: 25 years):</p>
                        <div class="comparison-grid">
                            <div class="comparison-column">
                                <strong>Source Node</strong>
                                <div class="field-group">
                                    <span class="field-label">Year:</span>
                                    <div class="field-value">{selectedEdge.source.year || 'Unknown'}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Date Begin:</span>
                                    <div class="field-value">{selectedEdge.source.date_begin || 'N/A'}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Date End:</span>
                                    <div class="field-value">{selectedEdge.source.date_end || 'N/A'}</div>
                                </div>
                            </div>
                            <div class="comparison-column">
                                <strong>Target Node</strong>
                                <div class="field-group">
                                    <span class="field-label">Year:</span>
                                    <div class="field-value">{selectedEdge.target.year || 'Unknown'}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Date Begin:</span>
                                    <div class="field-value">{selectedEdge.target.date_begin || 'N/A'}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Date End:</span>
                                    <div class="field-value">{selectedEdge.target.date_end || 'N/A'}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                {/if}
                
                {#if expandedSimilarity === 'place'}
                    <div class="metadata-comparison">
                        <h6>Spatial Proximity Fields</h6>
                        <p class="comparison-note">Calculated using Haversine distance with Gaussian kernel (bandwidth: 400 km):</p>
                        <div class="comparison-grid">
                            <div class="comparison-column">
                                <strong>Source Node</strong>
                                <div class="field-group">
                                    <span class="field-label">Coordinates:</span>
                                    <div class="field-value">
                                        {#if getCoordinates(selectedEdge.source)}
                                            {@const coords = getCoordinates(selectedEdge.source)}
                                            {coords?.lat.toFixed(4)}, {coords?.lon.toFixed(4)}
                                            {#if !selectedEdge.source.place_lat || !selectedEdge.source.place_lon}
                                                <span class="gazetteer-badge" title="Coordinates from gazetteer">📍</span>
                                            {/if}
                                        {:else}
                                            N/A
                                        {/if}
                                    </div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Place Label:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.source.place_label)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Country:</span>
                                    <div class="field-value">{selectedEdge.source.country || 'N/A'}</div>
                                </div>
                            </div>
                            <div class="comparison-column">
                                <strong>Target Node</strong>
                                <div class="field-group">
                                    <span class="field-label">Coordinates:</span>
                                    <div class="field-value">
                                        {#if getCoordinates(selectedEdge.target)}
                                            {@const coords = getCoordinates(selectedEdge.target)}
                                            {coords?.lat.toFixed(4)}, {coords?.lon.toFixed(4)}
                                            {#if !selectedEdge.target.place_lat || !selectedEdge.target.place_lon}
                                                <span class="gazetteer-badge" title="Coordinates from gazetteer">📍</span>
                                            {/if}
                                        {:else}
                                            N/A
                                        {/if}
                                    </div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Place Label:</span>
                                    <div class="field-value">{formatArrayField(selectedEdge.target.place_label)}</div>
                                </div>
                                <div class="field-group">
                                    <span class="field-label">Country:</span>
                                    <div class="field-value">{selectedEdge.target.country || 'N/A'}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                {/if}
                
                <p class="score-explanation">
                    This edge represents a weighted combination of the four similarity vectors. The combined score is calculated using the formula:
                    G = α × S<sub>text</sub> + β × S<sub>date</sub> + γ × S<sub>place</sub> + δ × S<sub>user</sub>
                    <br>(User interactions not shown here as this is pre-computed data with default weights α=0.5, β=0.2, γ=0.2, δ=0.1)
                </p>
            </div>
        </div>
    {:else}
        <p class="instruction">Click on an edge (connection line) in the graph above to see the detailed similarity breakdown between two nodes.</p>
    {/if}

    <p>
        This is a different approach compared to filtering or faceting mechanisms commonly used in digital archives, where the connections are pre-defined and static. Here, the relationships are fluid and can be adjusted in real-time. Records might cluster across different collections if they share strong similarities in their attributes.
    </p>

    <h3>The Fourth Vector: Visitor Interactions</h3>

    <p>
        Beyond the three computational similarity vectors (textual, temporal, and spatial), the Graphical Archive includes a <strong>fourth vector based on visitors' browsing behavior</strong>. This creates a personalized layer that adapts the network to each visitor's individual exploration patterns.
    </p>

    <p>
        The metadata proximity calculations we've explored (textual, temporal, and spatial similarities) are pre-computed and stored in a middleware layer that provides the archive's initial shape. However, visitor interactions also play a crucial role in determining which connections become relevant during exploration. This is where collection boundaries blur, transforming the archive into a dynamic graphical space that adapts to visitors' interests in real-time.
    </p>

    <div class="methodology-callouts">
        <details class="methodology-detail">
            <summary>
                <strong>User Interaction Similarity Calculation</strong>
                <span class="expand-icon">▶</span>
            </summary>
            <div class="detail-content">
                <p>
                    As visitors navigate the archive—viewing items, bookmarking records, and exploring relationships—the system tracks which items they engage with. It then calculates similarity between items based on <strong>co-occurrence patterns</strong>: items that appear together in a browsing session are considered related.
                </p>
                <p><strong>Tracked interactions:</strong></p>
                <ul>
                    <li><code>Views</code> — Items clicked on or examined in detail</li>
                    <li><code>Bookmarks</code> — Items explicitly saved for later reference</li>
                    <li><code>View sequence</code> — The temporal order of exploration (sliding window)</li>
                </ul>
                <p>
                    The algorithm uses a <strong>sliding window approach</strong> for views: items viewed close together in time (within 5 items) are considered co-occurring. For bookmarks, all pairs of bookmarked items are treated as related.
                </p>
                <p class="formula">
                    <span bind:this={formulaSuserDetail}></span>
                </p>
                <p>
                    This creates a <strong>collaborative filtering effect</strong> based on individual sessions rather than aggregate user data. Items a visitor has engaged with become more strongly connected, influencing which neighbors are suggested for subsequent items they explore.
                </p>
            </div>
        </details>

        <details class="methodology-detail">
            <summary>
                <strong>Privacy & Data Storage</strong>
                <span class="expand-icon">▶</span>
            </summary>
            <div class="detail-content">
                <p class="note">
                    <strong>Privacy-first architecture:</strong> All interaction tracking is <em>session-based only</em>. Browsing history is stored exclusively in the browser's <code>sessionStorage</code>, which is automatically cleared when the tab or browser window is closed.
                </p>
                <p>
                    <strong>Implementation characteristics:</strong>
                </p>
                <ul>
                    <li>No data is sent to external servers or databases</li>
                    <li>No cookies are set for tracking across sessions</li>
                    <li>Exploration patterns are never stored permanently</li>
                    <li>Each visitor's personalized network remains isolated</li>
                    <li>Closing the browser resets all interactions to zero</li>
                </ul>
                <p>
                    <strong>Trade-off:</strong> Because interaction data is session-only, the user similarity vector cannot "train" or permanently modify the archive's network structure. Each visit starts fresh. This architectural choice prioritizes privacy over personalization persistence.
                </p>
                <p>
                    Visitors can reset their current session's interaction data at any time by refreshing the page or closing and reopening the browser tab.
                </p>
            </div>
        </details>

        <details class="methodology-detail">
            <summary>
                <strong>Dynamic Weight Adjustment</strong>
                <span class="expand-icon">▶</span>
            </summary>
            <div class="detail-content">
                <p>
                    The main archive interface provides interactive sliders to adjust the relative weights of all four similarity vectors. This enables exploration of the archive through different analytical lenses:
                </p>
                <ul>
                    <li><strong>High textual weight</strong> → Prioritize items with similar topics, keywords, and descriptions</li>
                    <li><strong>High temporal weight</strong> → Emphasize items from similar time periods</li>
                    <li><strong>High spatial weight</strong> → Focus on geographic clustering</li>
                    <li><strong>High user interaction weight</strong> → Surface items related to browsing patterns</li>
                </ul>
                <p>
                    The final "Good Neighbor Index" is calculated using adjustable weights for each similarity dimension:
                </p>
                <p class="formula">
                    <span bind:this={formulaGDynamic}></span>
                </p>
                <p>
                    The weights (α, β, γ, δ) can be freely adjusted to explore different perspectives. For example, the backend pre-computes neighbors using α=0.5, β=0.2, γ=0.2, δ=0.1, but these can be modified in real-time to emphasize different dimensions—whether prioritizing textual similarity, temporal proximity, spatial clustering, or user interaction patterns.
                </p>
                <p>
                    When weights are adjusted, the network visualization updates in real-time, reshaping the graph to reflect the chosen balance between computational similarity and personal exploration patterns.
                </p>
            </div>
        </details>
    </div>


    <h3>Interactive Demo: See It in Action</h3>

    <p>
        The demonstration below shows how user interactions dynamically reshape item recommendations. Click on recommended items to simulate browsing behavior, and adjust the weight sliders to see how different similarity dimensions affect the ranking.
    </p>

    <div class="methodology-callouts">
        <details class="methodology-detail">
            <summary>
                <strong>How the Weight Sliders Work</strong>
                <span class="expand-icon">▶</span>
            </summary>
            <div class="detail-content">
                <p>
                    The weight sliders allow exploration of how different similarity dimensions affect recommendations. The sliders can be set to any values—the system automatically normalizes them to ensure they sum to 1.0 for the calculation.
                </p>
                <p><strong>Example normalization:</strong></p>
                <ul>
                    <li><strong>Input:</strong> Textual=75, Temporal=45, Spatial=55, User=15 (sum = 190)</li>
                    <li><strong>Normalized:</strong> 0.395, 0.237, 0.289, 0.079 (sum = 1.0)</li>
                </ul>
                <p class="formula">
                    <span bind:this={formulaGExample}></span>
                </p>
                <p>
                    The resulting G coefficient ranges from 0 to 1, displayed as percentages in the recommendation cards. The <strong>S<sub>user</sub></strong> value is calculated dynamically based on clicked items: items that have been clicked receive S<sub>user</sub>=1.0, while items sharing neighbors with clicked items receive values between 0.3 and 0.9.
                </p>
                <p>
                    <strong>Experiment:</strong> Set all weights to 0 except one at 100 to see recommendations based purely on a single dimension. Or distribute weights evenly (all at 25) to give equal importance to all factors.
                </p>
            </div>
        </details>
    </div>
</div>

<!-- Demo Section -->

    {#if demoSelectedItem}
        <div class="demo-container">
            <!-- Left: Main Content -->
            <div class="demo-main-content">
                <div class="demo-selected">
                    <div class="demo-thumbnail">
                        {#if demoSelectedItem.thumbnail}
                            <img src={demoSelectedItem.thumbnail} alt={formatTitle(demoSelectedItem)} />
                        {:else}
                            <div class="no-thumbnail">No image</div>
                        {/if}
                    </div>
                    <div class="demo-details">
                        <h4>{formatTitle(demoSelectedItem)}</h4>
                        <p class="demo-meta">
                            {demoSelectedItem.year || 'Unknown year'} • {demoSelectedItem.country || 'Unknown location'}
                        </p>
                        <p class="demo-instruction">
                            💡 Click on recommended items to simulate browsing. Items you click will get higher similarity scores. Use the sliders below to adjust the weight balance.
                        </p>
                    </div>
                </div>

                <div class="demo-weights">
                    <h5>Similarity Vector Weights</h5>
                    <div class="weight-controls">
                    <div class="weight-item">
                        <label>
                            <span class="weight-label">Textual</span>
                            <input 
                                type="range" 
                                min="0" 
                                max="100" 
                                bind:value={demoWeights.text}
                                on:input={handleWeightChange}
                                step="5"
                            />
                            <span class="weight-value">{demoWeights.text.toFixed(0)}%</span>
                        </label>
                    </div>
                    <div class="weight-item">
                        <label>
                            <span class="weight-label">Temporal</span>
                            <input 
                                type="range" 
                                min="0" 
                                max="100" 
                                bind:value={demoWeights.date}
                                on:input={handleWeightChange}
                                step="5"
                            />
                            <span class="weight-value">{demoWeights.date.toFixed(0)}%</span>
                        </label>
                    </div>
                    <div class="weight-item">
                        <label>
                            <span class="weight-label">Spatial</span>
                            <input 
                                type="range" 
                                min="0" 
                                max="100" 
                                bind:value={demoWeights.place}
                                on:input={handleWeightChange}
                                step="5"
                            />
                            <span class="weight-value">{demoWeights.place.toFixed(0)}%</span>
                        </label>
                    </div>
                    <div class="weight-item user-weight">
                        <label>
                            <span class="weight-label">User Interaction</span>
                            <input 
                                type="range" 
                                min="0" 
                                max="100" 
                                bind:value={demoWeights.user}
                                on:input={handleWeightChange}
                                step="5"
                            />
                            <span class="weight-value highlight">{demoWeights.user.toFixed(0)}%</span>
                        </label>
                        <span class="weight-note">💡 Adjust to see how browsing patterns affect results</span>
                    </div>
                </div>
                <button class="reset-button" on:click={resetDemo}>Reset Demo</button>
            </div>
            </div>

            <!-- Right: Recommendations Sidebar -->
            <div class="demo-recommendations">
                <div class="recommendations-header">
                    <h5>Recommended Neighbors</h5>
                    <div class="display-control">
                        <label>
                            <span class="control-label">Show items: <strong>{demoDisplayCount}</strong></span>
                            <input 
                                type="range" 
                                min="8" 
                                max="50" 
                                bind:value={demoDisplayCount}
                                on:input={handleDisplayCountChange}
                                step="1"
                                class="count-slider"
                            />
                        </label>
                    </div>
                </div>
                <div class="recommendations-grid">
                    {#each demoRecommendations as rec, i}
                        <div 
                            class="recommendation-card"
                            class:clicked={demoClickedItems.has(rec.id)}
                            class:user-influenced={rec.userScore > 0}
                            on:click={() => handleDemoItemClick(rec.id)}
                            on:keydown={(e) => e.key === 'Enter' || e.key === ' ' ? (e.preventDefault(), handleDemoItemClick(rec.id)) : null}
                            role="button"
                            tabindex="0"
                        >
                            {#if rec.item.thumbnail}
                                <img src={rec.item.thumbnail} alt={formatTitle(rec.item)} />
                            {:else}
                                <div class="card-no-thumbnail">No image</div>
                            {/if}
                            <div class="card-info">
                                <div class="card-title">{formatTitle(rec.item)}</div>
                                <div class="card-score">
                                    Neighborness: {(rec.weightedScore * 100).toFixed(0)}%
                                    {#if rec.userScore > 0}
                                        <span class="user-badge" title="Boosted by user interactions">👤</span>
                                    {/if}
                                </div>
                                {#if initialPositions.has(rec.id) && initialPositions.get(rec.id) !== (i + 1)}
                                    <div class="position-indicator" title="Initial position: #{initialPositions.get(rec.id)}">
                                        <span class="position-badge">was #{initialPositions.get(rec.id)}</span>
                                        {#if (initialPositions.get(rec.id) ?? 0) > (i + 1)}
                                            <span class="position-arrow up">↑</span>
                                        {:else}
                                            <span class="position-arrow down">↓</span>
                                        {/if}
                                    </div>
                                {/if}
                            </div>
                        </div>
                    {/each}
                </div>
                <p class="demo-legend">
                    <span class="legend-item"><span class="legend-badge user-influenced-badge"></span> Influenced by your interactions</span>
                    <span class="legend-item"><span class="legend-badge clicked-badge"></span> Already viewed</span>
                </p>
            </div>
        </div>
    {:else}
        <p class="instruction">Loading interactive demo...</p>
    {/if}

<!-- End of Demo Section -->

    <div class="text-body">
    <p>
        The number of displayed neighbors directly impacts the balance between precision and discovery. Showing only the top 8 neighbors emphasizes the strongest relationships, making it easier for clicked items to dominate the recommendations; ideal for focused exploration within tightly related clusters (e.g., same collection, time period, or location). In contrast, expanding to 50 neighbors surfaces weaker but potentially interesting connections, enabling broader discovery across the archive's scattered elements. The optimal choice depends entirely on the visitor's exploration strategy: depth versus breadth, familiar versus unexpected.
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
    </div>
</article>

<style>
    .about-page {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
        line-height: 1.6;
    }

    .text-body {
        max-width: 800px;
        margin: 0 auto;
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

    .methodology-callouts {
        margin: 2rem 0;
    }

    .methodology-detail {
        margin-bottom: 1rem;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
        transition: all 0.3s ease;
    }

    .methodology-detail:hover {
        border-color: #0066cc;
        box-shadow: 0 2px 8px rgba(0, 102, 204, 0.1);
    }

    .methodology-detail summary {
        padding: 1rem 1.5rem;
        background-color: #f5f5f5;
        cursor: pointer;
        user-select: none;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 1.05rem;
        transition: background-color 0.2s ease;
    }

    .methodology-detail summary:hover {
        background-color: #e8f4ff;
    }

    .methodology-detail[open] summary {
        background-color: #e8f4ff;
        border-bottom: 2px solid #0066cc;
    }

    .expand-icon {
        color: #0066cc;
        font-size: 0.8rem;
        transition: transform 0.3s ease;
    }

    .methodology-detail[open] .expand-icon {
        transform: rotate(90deg);
    }

    .detail-content {
        padding: 1.5rem;
        background-color: white;
        line-height: 1.6;
    }

    .detail-content p {
        margin-bottom: 1rem;
    }

    .detail-content ul {
        margin: 1rem 0;
        padding-left: 2rem;
    }

    .detail-content li {
        margin-bottom: 0.5rem;
    }

    .detail-content code {
        background-color: #f5f5f5;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.9rem;
        color: #d63384;
    }

    .detail-content a {
        color: #0066cc;
        text-decoration: none;
        font-weight: 500;
        border-bottom: 1px dashed #0066cc;
    }

    .detail-content a:hover {
        border-bottom-style: solid;
    }

    .formula {
        background-color: #f9f9f9;
        padding: 0.75rem 1rem;
        border-left: 4px solid #0066cc;
        margin: 1rem 0;
        font-family: 'Georgia', serif;
    }

    .note {
        background-color: #fff9e6;
        border-left: 4px solid #ffc107;
        padding: 0.75rem 1rem;
        margin: 1rem 0;
        font-size: 0.95rem;
    }

    .note strong {
        color: #856404;
    }

    .final-formula {
        margin-top: 2rem;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 8px;
        color: white;
    }

    .final-formula strong {
        display: block;
        margin-bottom: 1rem;
        font-size: 1.2rem;
    }

    .formula.main {
        background-color: rgba(255, 255, 255, 0.15);
        border-left: 4px solid white;
        font-size: 1.1rem;
    }

    .formula-note {
        margin-top: 1rem;
        font-size: 0.9rem;
        opacity: 0.95;
        line-height: 1.6;
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
        transition: all 0.2s ease;
    }

    .score-item.clickable {
        cursor: pointer;
        border: 2px solid transparent;
    }

    .score-item.clickable:hover {
        background-color: #e8f4ff;
        border-color: #0066cc;
        transform: translateX(4px);
    }

    .hint {
        font-size: 0.75rem;
        color: #0066cc;
        font-weight: normal;
        font-style: italic;
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

    .metadata-comparison {
        margin-top: 1.5rem;
        padding: 1.5rem;
        background-color: #f0f8ff;
        border-radius: 6px;
        border-left: 4px solid #0066cc;
        animation: slideDown 0.3s ease;
    }

    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .metadata-comparison h6 {
        font-size: 1.1rem;
        margin-bottom: 0.75rem;
        color: #004499;
    }

    .comparison-note {
        font-size: 0.85rem;
        color: #666;
        font-style: italic;
        margin-bottom: 1rem;
    }

    .comparison-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
    }

    @media (max-width: 768px) {
        .comparison-grid {
            grid-template-columns: 1fr;
        }
    }

    .comparison-column {
        background-color: white;
        padding: 1rem;
        border-radius: 6px;
    }

    .comparison-column > strong {
        display: block;
        margin-bottom: 1rem;
        color: #004499;
        font-size: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
    }

    .field-group {
        margin-bottom: 0.75rem;
    }

    .field-label {
        display: block;
        font-weight: 600;
        color: #555;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
    }

    .field-value {
        padding: 0.5rem;
        background-color: #f9f9f9;
        border-radius: 4px;
        font-size: 0.9rem;
        color: #333;
        word-wrap: break-word;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .gazetteer-badge {
        font-size: 0.9rem;
        opacity: 0.7;
        cursor: help;
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

    /* Interactive Demo Styles */
    .demo-container {
        margin: 2rem auto;
        max-width: 1400px;
        padding: 2rem;
        background-color: #f8f9fa;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        display: grid;
        grid-template-columns: 1fr 380px;
        gap: 2rem;
    }

    @media (max-width: 1200px) {
        .demo-container {
            grid-template-columns: 1fr;
            max-width: 800px;
        }
    }

    .demo-main-content {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .demo-selected {
        background-color: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }

    .demo-thumbnail {
        width: 100%;
        background-color: #000;
        aspect-ratio: 16/9;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .demo-thumbnail img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        margin: 0;
        box-shadow: none;
    }

    .no-thumbnail, .card-no-thumbnail {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #e0e0e0;
        color: #666;
        font-size: 0.85rem;
    }

    .demo-details {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
    }

    .demo-details h4 {
        margin: 0 0 0.5rem 0;
        font-size: 1.4rem;
        color: #333;
        line-height: 1.3;
    }

    .demo-meta {
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #e0e0e0;
    }

    .demo-instruction {
        background-color: #fff9e6;
        padding: 0.75rem 1rem;
        border-left: 4px solid #ffc107;
        border-radius: 4px;
        font-size: 0.95rem;
        color: #856404;
        margin: 0;
    }

    .demo-weights {
        background-color: white;
        padding: 1.5rem;
        border-radius: 8px;
    }

    .demo-weights h5 {
        margin: 0 0 1rem 0;
        font-size: 1.1rem;
        color: #333;
    }

    .weight-controls {
        display: grid;
        gap: 1rem;
    }

    .weight-item {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .weight-item label {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .weight-label {
        font-weight: 600;
        color: #555;
        min-width: 120px;
    }

    .weight-item input[type="range"] {
        flex: 1;
        height: 6px;
        border-radius: 3px;
        background: #e0e0e0;
        outline: none;
        -webkit-appearance: none;
        appearance: none;
    }

    .weight-item input[type="range"]::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #0066cc;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    .weight-item input[type="range"]::-moz-range-thumb {
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #0066cc;
        cursor: pointer;
        border: none;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }

    .weight-value {
        font-weight: 700;
        color: #0066cc;
        min-width: 50px;
        text-align: right;
    }

    .weight-value.highlight {
        color: #ff6b35;
        font-size: 1.1rem;
    }

    .weight-item.user-weight {
        padding-top: 0.5rem;
        border-top: 2px solid #e0e0e0;
    }

    .weight-note {
        font-size: 0.85rem;
        color: #ff6b35;
        font-style: italic;
        margin-left: 120px;
    }

    .reset-button {
        margin-top: 1rem;
        padding: 0.75rem 1.5rem;
        background-color: #dc3545;
        color: white;
        border: none;
        border-radius: 6px;
        font-size: 0.95rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .reset-button:hover {
        background-color: #c82333;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3);
    }

    .demo-recommendations {
        background-color: white;
        border-radius: 8px;
        padding: 1rem;
    }

    .recommendations-header {
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #e0e0e0;
    }

    .recommendations-header h5 {
        margin: 0 0 0.75rem 0;
        font-size: 1rem;
        color: #333;
    }

    .display-control {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .display-control label {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        font-size: 0.85rem;
        color: #666;
        width: 100%;
    }

    .control-label {
        display: flex;
        justify-content: space-between;
    }

    .control-label strong {
        color: #0066cc;
        font-weight: 600;
    }

    .count-slider {
        width: 100%;
        height: 4px;
        cursor: pointer;
    }

    .recommendations-grid {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        max-height: 800px;
        overflow-y: auto;
        padding-right: 0.5rem;
    }

    /* Custom scrollbar styling */
    .recommendations-grid::-webkit-scrollbar {
        width: 8px;
    }

    .recommendations-grid::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }

    .recommendations-grid::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }

    .recommendations-grid::-webkit-scrollbar-thumb:hover {
        background: #555;
    }

    @media (max-width: 1200px) {
        .recommendations-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            max-height: none;
        }
    }

    .recommendation-card {
        background-color: #f8f9fa;
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        gap: 0.75rem;
        min-height: 94px;
    }

    @media (max-width: 1200px) {
        .recommendation-card {
            flex-direction: column;
        }
    }

    .recommendation-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 6px 16px rgba(0, 102, 204, 0.2);
        border-color: #0066cc;
    }

    .recommendation-card.clicked {
        border-color: #28a745;
        background-color: #e8f5e9;
    }

    .recommendation-card.user-influenced {
        border-color: #ff6b35;
        box-shadow: 0 0 0 2px rgba(255, 107, 53, 0.2);
    }

    .recommendation-card img {
        width: 168px;
        height: 94px;
        object-fit: cover;
        margin: 0;
        box-shadow: none;
        flex-shrink: 0;
    }

    .card-no-thumbnail {
        width: 168px;
        height: 94px;
        background-color: #e0e0e0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #999;
        font-size: 0.75rem;
        flex-shrink: 0;
    }

    @media (max-width: 1200px) {
        .recommendation-card img {
            width: 100%;
            height: 140px;
        }

        .card-no-thumbnail {
            width: 100%;
            height: 140px;
        }
    }

    .card-info {
        padding: 0.75rem;
        flex: 1;
        display: flex;
        flex-direction: column;
    }

    .card-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 0.5rem;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .card-score {
        font-size: 0.75rem;
        color: #666;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .user-badge {
        font-size: 1rem;
    }

    .position-indicator {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        margin-top: 0.5rem;
        font-size: 0.7rem;
        color: #888;
    }

    .position-badge {
        background-color: rgba(0, 102, 204, 0.1);
        border: 1px solid rgba(0, 102, 204, 0.3);
        padding: 0.1rem 0.4rem;
        border-radius: 3px;
        font-weight: 500;
    }

    .position-arrow {
        font-size: 0.9rem;
        font-weight: bold;
    }

    .position-arrow.up {
        color: #28a745;
    }

    .position-arrow.down {
        color: #dc3545;
    }

    .demo-legend {
        display: flex;
        gap: 1.5rem;
        font-size: 0.85rem;
        color: #666;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e0e0e0;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .legend-badge {
        display: inline-block;
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid;
    }

    .user-influenced-badge {
        border-color: #ff6b35;
        background-color: rgba(255, 107, 53, 0.1);
    }

    .clicked-badge {
        border-color: #28a745;
        background-color: #e8f5e9;
    }
</style>