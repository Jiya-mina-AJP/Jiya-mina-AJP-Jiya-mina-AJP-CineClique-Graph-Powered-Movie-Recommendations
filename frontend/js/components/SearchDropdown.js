export class SearchDropdown {
    constructor(containerId, onMovieSelect) {
        this.container = document.getElementById(containerId);
        this.onMovieSelect = onMovieSelect;
        this.render();
        this.setupEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="search-input-wrapper">
                <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input type="text" id="movie-search" class="search-input" placeholder="Search for movies to add..." autocomplete="off">
            </div>
            <div class="dropdown-menu" id="search-dropdown"></div>
        `;
        this.input = document.getElementById('movie-search');
        this.dropdown = document.getElementById('search-dropdown');
    }

    setupEventListeners() {
        this.input.addEventListener('input', (e) => this.handleSearch(e.target.value));
        
        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.closeDropdown();
            }
        });

        // Open dropdown on focus if there's text
        this.input.addEventListener('focus', () => {
            if (this.input.value.trim().length > 0) {
                this.handleSearch(this.input.value);
            }
        });
    }

    async handleSearch(query) {
        query = query.trim().toLowerCase();
        
        if (query.length === 0) {
            this.closeDropdown();
            return;
        }

        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const results = await response.json();

            // Render instantly with empty posters to avoid UI lockup
            results.forEach(m => m.poster = '');
            this.currentResults = results;
            this.renderResults(results);
            this.openDropdown();

            // Asynchronously fetch posters in the background
            results.forEach(movie => {
                fetch(`/api/poster?title=${encodeURIComponent(movie.title)}`)
                    .then(res => res.json())
                    .then(data => {
                        movie.poster = data.poster;
                        const imgEl = this.dropdown.querySelector(`.dropdown-item[data-id="${movie.id}"] .dropdown-item-poster`);
                        if (imgEl && data.poster) {
                            imgEl.src = data.poster;
                        }
                    })
                    .catch(err => console.error(err));
            });
        } catch (error) {
            console.error("Failed to search movies:", error);
            this.dropdown.innerHTML = `<div class="no-results">Error performing search</div>`;
            this.openDropdown();
        }
    }

    renderResults(results) {
        if (results.length === 0) {
            this.dropdown.innerHTML = `<div class="no-results">No movies found</div>`;
            return;
        }

        this.dropdown.innerHTML = results.map(movie => `
            <div class="dropdown-item" data-id="${movie.id}">
                <img src="${movie.poster}" alt="${movie.title}" class="dropdown-item-poster" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'40\\' height=\\'60\\'><rect fill=\\'%23334155\\' width=\\'40\\' height=\\'60\\'/></svg>'">
                <div class="dropdown-item-info">
                    <h4>${movie.title}</h4>
                    <p>${movie.year} • ★ ${movie.rating} • ${movie.genre}</p>
                </div>
            </div>
        `).join('');

        // Add click events to items
        const items = this.dropdown.querySelectorAll('.dropdown-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const movieId = item.getAttribute('data-id');
                const movie = this.currentResults.find(m => m.id == movieId);
                if (movie) {
                    this.onMovieSelect(movie);
                    this.closeDropdown();
                    this.input.value = '';
                }
            });
        });
    }

    openDropdown() {
        this.dropdown.classList.add('active');
    }

    closeDropdown() {
        this.dropdown.classList.remove('active');
    }
}
