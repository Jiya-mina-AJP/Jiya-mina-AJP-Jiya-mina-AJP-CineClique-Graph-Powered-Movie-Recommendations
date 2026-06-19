export class MoviePanel {
    constructor(listId, countId) {
        this.listEl = document.getElementById(listId);
        this.countEl = document.getElementById(countId);
        this.addedMovies = []; // Could be initialized from local storage or DB
        this.mode = 'collection'; // 'collection' or 'watchlist'
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
            const msg = this.mode === 'watchlist' 
                ? "Your watchlist is empty. Bookmark movies from the recommendations page!"
                : "No movies added yet. Search and select a movie to get started!";
            this.listEl.innerHTML = `
                <div class="empty-state">
                    <p>${msg}</p>
                </div>
            `;
            return;
        }

        this.listEl.innerHTML = this.addedMovies.map((movie) => `
            <div class="movie-card" data-id="${movie.id}">
                <img src="${movie.poster || `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='80' height='120'><rect fill='%23334155' width='80' height='120'/></svg>`}" alt="${movie.title}" class="movie-card-poster" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'80\\' height=\\'120\\'><rect fill=\\'%23334155\\' width=\\'80\\' height=\\'120\\'/></svg>'">
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
                    ${this.mode === 'collection' ? `
                    <div class="movie-card-user-rating" style="margin-top: 10px;">
                        <span style="font-size: 12px; color: #94a3b8;">Your Rating:</span>
                        <div class="stars" data-movie-id="${movie.id}" style="color: #c2a878; cursor: pointer; font-size: 18px;">
                            ${[1,2,3,4,5].map(star => 
                                `<span class="star" data-rating="${star}" style="opacity: ${movie.user_rating >= star ? 1 : 0.3}">★</span>`
                            ).join('')}
                        </div>
                    </div>` : ''}
                </div>
            </div>
        `).join('');

        // Setup remove buttons
        const removeBtns = this.listEl.querySelectorAll('.remove-btn');
        removeBtns.forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = btn.getAttribute('data-remove-id');
                if (this.mode === 'watchlist') {
                    const email = localStorage.getItem('user_email');
                    if (email) {
                        try {
                            await fetch('/api/watchlist', {
                                method: 'DELETE',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ email: email, movie_id: id })
                            });
                        } catch(err) { console.error(err); }
                    }
                }
                this.removeMovie(id);
            });
        });

        // Setup rating stars
        const stars = this.listEl.querySelectorAll('.star');
        stars.forEach(star => {
            star.addEventListener('click', async (e) => {
                const rating = parseInt(e.target.getAttribute('data-rating'));
                const movieId = e.target.closest('.stars').getAttribute('data-movie-id');
                const username = localStorage.getItem('user_email');
                
                if (!username) {
                    alert("Please login first to rate movies!");
                    return;
                }

                // Optimistic UI update
                const movie = this.addedMovies.find(m => m.id == movieId);
                if (movie) movie.user_rating = rating;
                this.render();

                try {
                    await fetch('/api/rate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user_id: username, movie_id: movieId, rating: rating })
                    });
                } catch(err) {
                    console.error("Failed to submit rating", err);
                }
            });
        });
    }
}
