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

    let vectorMatrix: HTMLElement;
    
    const matrixLatex = '\\begin{bmatrix} \\vec{\\text{metadata}} \\parallel \\vec{\\text{spatial}} \\parallel \\vec{\\text{temporal}} \\parallel \\vec{\\text{interaction}} \\end{bmatrix}';

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

    <p>
        We are representing each archival item as a <strong>node</strong> in a network graph. The complexity of the archival node is totally arbitrary, and can be understood as a "digital object" in the terms of Yuk Hui, that is: "objects that take shape on a screen or hide in the back end of a computer program, composed of data and metadata regulated by structures or schemas." <a href="#ref-huiExistenceDigitalObjects2016" class="citation"><sup>1</sup></a>
    </p>

    <p>
        For instance, the node with the title "Receipt to Irish Transport Workers' Union" encapsulates various attributes such as:
    </p>

    <img src={nodeImage} alt="Representation of a node in the Graphical Archive" />

    <pre><code class="language-json">{`{
    "id": "/139/_ff36jk99d",
    "title": [
        "Receipt to Irish Transport Workers' Union"
    ],
    "creator": [
        "Hopkins and Hopkins"
    ],
    "description": "Hopkins and Hopkins receipt to Irish Transport Workers' Union for the purchase of silver and gold medals.  John J. O'Neill was one of the founding members and a general secretary of the the Irish Transport and General Workers Union. He was one of three trustees to the deeds of Liberty Hall. He lived at 61 Ballybough Road, Dublin and took part in the Rising fighting at both Liberty Hall and the GPO. After the Rising he was interned in Frongoch.",
    "year": "Unknown Year",
    "timespan": [
        "Unknown Timespan"
    ],
    "language": [
        "en"
    ],
    "type": "TEXT",
    "concepts": [],
    "place": {
        "en": [
            "Dublin, Ireland",
            "Frongoch, Bala, Gwynedd"
        ]
    },
    "place_lat": 53.3478,
    "place_lon": -6.25972,
    "country": "Ireland",
    "collection": "139_DRI_UGC_1916_memorabilia",
    "thumbnail": "https://api.europeana.eu/thumbnail/v2/url.json?uri=http%3A%2F%2Frepository.dri.ie%2Fobjects%2Fff36jk99d%2Ffiles%2Ffj23kg83r%2Fdownload%3Ftype%3Dsurrogate&type=TEXT",
    "link": "https://doi.org/10.7486/DRI.ff36jk99d",
    "rights": "http://creativecommons.org/publicdomain/zero/1.0/",
    "iiif_manifest": "https://iiif.europeana.eu/presentation/139/_ff36jk99d/manifest",
    "creators": [
        "Terry O'Neill"
    ],
    "date_begin": "1938-01-28",
    "date_end": "1938-07-25",
    "place_label": "Dublin, Ireland"
}`}</code></pre>

    <p>
        The node is an abstraction, a capsule, that contains all the relevant metadata and the connections to the digital artifact itself (e.g., the link to the Europeana record, the IIIF manifest, etc.).
    </p>

    <p>
        To avoid orphan nodes, every object must be connected to at least one other object through <strong>edges</strong>. Edges represent variable-strength relationships between nodes based on shared attributes. The proximity, or neighborness, of nodes is determined by a very simple score based on four vectors:
    </p>

    <div class="vectors-matrix" bind:this={vectorMatrix}></div>

    <p>
        Each vector can be weighted differently based on user preferences, allowing for a dynamic exploration of the archive based on different relational criteria.
    </p>

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