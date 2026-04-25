export class MoviePanel {
    constructor(listId, countId) {
        this.listEl = document.getElementById(listId);
        this.countEl = document.getElementById(countId);
        this.addedMovies = []; // Could be initialized from local storage or DB
    }

    addMovie(movie) {
        // Prevent duplicates
        if (this.addedMovies.some(m => m.id === movie.id)) {
            return false;
        }

        this.addedMovies.push(movie);
        this.render();
        return true;
    }

    removeMovie(id) {
        this.addedMovies = this.addedMovies.filter(m => m.id != id);
        this.render();
    }

    render() {
        this.countEl.textContent = this.addedMovies.length;

        if (this.addedMovies.length === 0) {
            this.listEl.innerHTML = `
                <div class="empty-state">
                    <p>No movies added yet. Search and select a movie to get started!</p>
                </div>
            `;
            return;
        }

        this.listEl.innerHTML = this.addedMovies.map((movie) => `
            <div class="movie-card" data-id="${movie.id}">
                <img src="${movie.poster}" alt="${movie.title}" class="movie-card-poster" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'80\\' height=\\'120\\'><rect fill=\\'%23334155\\' width=\\'80\\' height=\\'120\\'/></svg>'">
                <div class="movie-card-content">
                    <button class="remove-btn" title="Remove" data-remove-id="${movie.id}">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                    <h3 class="movie-card-title">${movie.title}</h3>
                    <div class="movie-card-year">${movie.year} • ★ ${movie.rating}</div>
                    <div class="movie-card-genre">${movie.genre}</div>
                </div>
            </div>
        `).join('');

        // Setup remove buttons
        const removeBtns = this.listEl.querySelectorAll('.remove-btn');
        removeBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = btn.getAttribute('data-remove-id');
                this.removeMovie(id);
            });
        });
    }
}
