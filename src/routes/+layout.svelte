<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	
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
    <div class="pt-6 border-t border-gray-200 flex flex-col sm:flex-row justify-center items-center gap-2 sm:gap-4 text-xs text-gray-500">
      <p>
        © {new Date().getFullYear()} Jairo Antonio Melo Flórez
      </p>
      <div class="flex items-center gap-3">
        <a href="https://github.com/jairomelo/graphical-archive/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" class="hover:text-gray-900 transition-colors inline-flex items-center gap-1">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3">
            <path d="M8.75.75V2h.985c.304 0 .603.08.867.231l1.29.736c.038.022.08.033.124.033h2.234a.75.75 0 0 1 0 1.5h-.427l2.111 4.692a.75.75 0 0 1-.154.838l-.53-.53.529.531-.001.002-.002.002-.006.006-.006.005-.01.01-.045.04c-.21.176-.441.327-.686.45C14.556 10.78 13.88 11 13 11a4.498 4.498 0 0 1-2.023-.454 3.544 3.544 0 0 1-.686-.45l-.045-.04-.016-.015-.006-.006-.004-.004v-.001a.75.75 0 0 1-.154-.838L12.178 4.5h-.162c-.305 0-.604-.079-.868-.231l-1.29-.736a.245.245 0 0 0-.124-.033H8.75V13h2.5a.75.75 0 0 1 0 1.5h-6.5a.75.75 0 0 1 0-1.5h2.5V3.5h-.984a.245.245 0 0 0-.124.033l-1.289.737c-.265.15-.564.23-.869.23h-.162l2.112 4.692a.75.75 0 0 1-.154.838l-.53-.53.529.531-.001.002-.002.002-.006.006-.016.015-.045.04c-.21.176-.441.327-.686.45C4.556 10.78 3.88 11 3 11a4.498 4.498 0 0 1-2.023-.454 3.544 3.544 0 0 1-.686-.45l-.045-.04-.016-.015-.006-.006-.004-.004v-.001a.75.75 0 0 1-.154-.838L2.178 4.5H1.75a.75.75 0 0 1 0-1.5h2.234a.249.249 0 0 0 .125-.033l1.288-.737c.265-.15.564-.23.869-.23h.984V.75a.75.75 0 0 1 1.5 0Zm2.945 8.477c.285.135.718.273 1.305.273s1.02-.138 1.305-.273L13 6.327Zm-10 0c.285.135.718.273 1.305.273s1.02-.138 1.305-.273L3 6.327Z" />
          </svg>
          <span>Code: MIT</span>
        </a>
        <span class="text-gray-300">|</span>
        <a href="https://github.com/jairomelo/graphical-archive/blob/main/LICENSE-CONTENT" target="_blank" rel="noopener noreferrer" class="hover:text-gray-900 transition-colors inline-flex items-center gap-1">
          <i class="bi bi-cc-circle-fill"></i>
          <span>Content: CC BY-NC-SA 4.0</span>
        </a>
      </div>
    </div>
  </div>
</footer>
