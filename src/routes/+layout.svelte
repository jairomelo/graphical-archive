<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { items, edges } from '$lib/stores';
	
	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<!-- Header -->
<header class="p-4 space-y-4">
  <div class="flex justify-between items-center">
    <a href="/" class="text-2xl font-bold hover:opacity-80 transition-opacity" style="display: inline-block;">
      <img src={favicon} alt="Graphical Archive logo" class="navbar-logo"> 
      Graphical Archive
    </a>
    <nav class="flex items-center gap-6">
      <a href="/about" class="text-sm text-gray-600 hover:text-gray-900 transition-colors">About</a>
      <a href="https://github.com/jairomelo/graphical-archive" target="_blank" rel="noopener noreferrer" class="text-2xl text-gray-600 hover:text-gray-900 transition-colors" aria-label="GitHub repository">
        <i class="bi bi-github"></i>
      </a>
    </nav>
  </div>
</header>

<!-- Main Content -->
<main class="min-h-screen">
  {@render children()}
</main>

<!-- Footer -->
<footer class="mt-12 border-t border-gray-200 bg-gradient-to-b from-white to-gray-50">
  <div class="max-w-7xl mx-auto px-4 py-8">
    <!-- Main footer content -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-6">
      <!-- About section -->
      <div class="space-y-3">
        <div class="flex items-center gap-2 mb-3">
          <img src={favicon} alt="Logo" class="h-6 w-6">
          <h3 class="font-semibold text-gray-900">Graphical Archive</h3>
        </div>
        <p class="text-sm text-gray-600 leading-relaxed">
          A conceptual exploration of archival topology through relational proximity, 
          moving beyond traditional hierarchies toward network-based navigation.
        </p>
      </div>

      <!-- Project info -->
      <div class="space-y-3">
        <h3 class="font-semibold text-gray-900 text-sm uppercase tracking-wide">Project</h3>
        <ul class="space-y-2 text-sm">
          <li>
            <a href="/about" class="text-gray-600 hover:text-gray-900 transition-colors inline-flex items-center gap-1">
              <i class="bi bi-info-circle"></i>
              About
            </a>
          </li>
          <li>
            <a href="https://github.com/jairomelo/graphical-archive" target="_blank" rel="noopener noreferrer" class="text-gray-600 hover:text-gray-900 transition-colors inline-flex items-center gap-1">
              <i class="bi bi-github"></i>
              Source Code
            </a>
          </li>
          <li>
            <a href="https://github.com/jairomelo/graphical-archive/issues" target="_blank" rel="noopener noreferrer" class="text-gray-600 hover:text-gray-900 transition-colors inline-flex items-center gap-1">
              <i class="bi bi-bug"></i>
              Report Issues
            </a>
          </li>
        </ul>
      </div>

      <!-- Technical info -->
      <div class="space-y-3">
        <h3 class="font-semibold text-gray-900 text-sm uppercase tracking-wide">Built With</h3>
        <div class="flex flex-wrap gap-2">
          <span class="px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-md font-medium">SvelteKit</span>
          <span class="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-md font-medium">D3.js</span>
          <span class="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-md font-medium">Python</span>
          <span class="px-2 py-1 bg-purple-100 text-purple-700 text-xs rounded-md font-medium">Europeana API</span>
        </div>
        <p class="text-xs text-gray-500 mt-3 leading-relaxed">
          Data sourced from Europeana Collections. Network metrics computed using 
          semantic similarity, temporal distance, and user interaction patterns.
        </p>
      </div>
    </div>

    <!-- Bottom bar -->
    <div class="pt-6 border-t border-gray-200 flex flex-col sm:flex-row justify-between items-center gap-4 text-xs text-gray-500">
      <div class="flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
        <p>
          © {new Date().getFullYear()} Jairo Antonio Melo Flórez
        </p>
        <div class="flex items-center gap-3">
          <a href="https://github.com/jairomelo/graphical-archive/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" class="hover:text-gray-900 transition-colors">
            Code: MIT
          </a>
          <span class="text-gray-300">|</span>
          <a href="https://github.com/jairomelo/graphical-archive/blob/main/LICENSE-CONTENT" target="_blank" rel="noopener noreferrer" class="hover:text-gray-900 transition-colors">
            Content: CC BY-NC-SA 4.0
          </a>
        </div>
      </div>
      <div class="flex items-center gap-4">
        {#if $items.length > 0}
          <span class="inline-flex items-center gap-1">
            <i class="bi bi-diagram-3"></i>
            {$items.length} items
          </span>
          <span class="inline-flex items-center gap-1">
            <i class="bi bi-arrows-angle-contract"></i>
            {$edges.length} connections
          </span>
        {/if}
      </div>
    </div>
  </div>
</footer>
