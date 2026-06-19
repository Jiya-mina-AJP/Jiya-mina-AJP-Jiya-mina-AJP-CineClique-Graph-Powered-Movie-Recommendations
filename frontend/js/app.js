import { SearchDropdown } from './components/SearchDropdown.js';
import { MoviePanel } from './components/MoviePanel.js';

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the Movie Panel
    const moviePanel = new MoviePanel('movie-list', 'movie-count');

    const loginStatus = document.getElementById('login-status');
    const logoutBtn = document.getElementById('logout-btn');

    // Check if already logged in
    const existingUser = localStorage.getItem('user_email');
    if (!existingUser) {
        window.location.href = '/login.html';
        return; // Stop execution
    }

    let activeTab = 'collection';
    let collectionData = [];
    let watchlistData = [];

    const tabCollection = document.getElementById('tab-collection');
    const tabWatchlist = document.getElementById('tab-watchlist');
    const panelTitle = document.getElementById('panel-title');

    // Initialize user data
    const loadUserData = async () => {
        loginStatus.textContent = `Loading ${existingUser}'s collection...`;
        
        try {
            const res = await fetch(`/api/user_ratings?user_id=${encodeURIComponent(existingUser)}`);
            collectionData = await res.json();
            
            // Trigger poster fetches
            collectionData.forEach(m => {
                if (!m.poster) {
                    fetch(`/api/poster?title=${encodeURIComponent(m.title)}`)
                        .then(r => r.json())
                        .then(d => {
                            if (d.poster) {
                                m.poster = d.poster;
                                if (activeTab === 'collection') moviePanel.render();
                            }
                        });
                }
            });

            if (activeTab === 'collection') {
                moviePanel.addedMovies = collectionData;
                moviePanel.render();
            }
            loginStatus.textContent = `Logged in as ${existingUser}`;
        } catch(e) {
            console.error("Error fetching ratings:", e);
        }
    };

    const loadWatchlistData = async () => {
        try {
            const res = await fetch(`/api/watchlist?email=${encodeURIComponent(existingUser)}`);
            if (res.ok) {
                watchlistData = await res.json();
                
                watchlistData.forEach(m => {
                    if (!m.poster) {
                        fetch(`/api/poster?title=${encodeURIComponent(m.title)}`)
                            .then(r => r.json())
                            .then(d => {
                                if (d.poster) {
                                    m.poster = d.poster;
                                    if (activeTab === 'watchlist') moviePanel.render();
                                }
                            });
                    }
                });

                if (activeTab === 'watchlist') {
                    moviePanel.addedMovies = watchlistData;
                    moviePanel.render();
                }
            }
        } catch(e) {
            console.error("Error fetching watchlist:", e);
        }
    };

    tabCollection.addEventListener('click', () => {
        activeTab = 'collection';
        tabCollection.classList.add('active');
        tabCollection.style.borderBottomColor = '#c2a878';
        tabCollection.style.color = '#c2a878';
        
        tabWatchlist.classList.remove('active');
        tabWatchlist.style.borderBottomColor = 'transparent';
        tabWatchlist.style.color = '#94a3b8';
        
        panelTitle.textContent = "Your Collection";
        moviePanel.mode = 'collection';
        moviePanel.addedMovies = collectionData;
        moviePanel.render();
    });

    tabWatchlist.addEventListener('click', () => {
        activeTab = 'watchlist';
        tabWatchlist.classList.add('active');
        tabWatchlist.style.borderBottomColor = '#c2a878';
        tabWatchlist.style.color = '#c2a878';
        
        tabCollection.classList.remove('active');
        tabCollection.style.borderBottomColor = 'transparent';
        tabCollection.style.color = '#94a3b8';
        
        panelTitle.textContent = "Watch Later";
        moviePanel.mode = 'watchlist';
        moviePanel.addedMovies = watchlistData;
        moviePanel.render();
        loadWatchlistData(); // Refresh on click
    });

    loadUserData();
    loadWatchlistData();

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.removeItem('user_token');
            localStorage.removeItem('user_email');
            window.location.href = '/login.html';
        });
    }

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
