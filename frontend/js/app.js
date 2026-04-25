import { SearchDropdown } from './components/SearchDropdown.js';
import { MoviePanel } from './components/MoviePanel.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the Movie Panel
    const moviePanel = new MoviePanel('movie-list', 'movie-count');

    // Initialize the Search Dropdown
    const searchDropdown = new SearchDropdown(
        'search-container', 
        (selectedMovie) => {
            // Callback when a movie is selected
            moviePanel.addMovie(selectedMovie);
        }
    );

    const recBtn = document.getElementById('get-recommendations-btn');
    if (recBtn) {
        recBtn.addEventListener('click', () => {
            if (moviePanel.addedMovies.length === 0) {
                alert("Please add at least one movie first.");
                return;
            }
            // Save selected movies to session storage
            sessionStorage.setItem('selectedMovies', JSON.stringify(moviePanel.addedMovies));
            window.location.href = '/recommendations.html';
        });
    }
});
