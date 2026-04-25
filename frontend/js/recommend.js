document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('results-container');

    // Read from session storage
    const savedData = sessionStorage.getItem('selectedMovies');
    if (!savedData) {
        container.innerHTML = `<div class="error-state">No movies selected. <a href="/">Go back</a></div>`;
        return;
    }

    let selectedMovies;
    try {
        selectedMovies = JSON.parse(savedData);
    } catch (e) {
        container.innerHTML = `<div class="error-state">Error reading selection. <a href="/">Go back</a></div>`;
        return;
    }

    if (selectedMovies.length === 0) {
        container.innerHTML = `<div class="error-state">No movies selected. <a href="/">Go back</a></div>`;
        return;
    }

    const movieIds = selectedMovies.map(m => m.id);

    try {
        // Fetch recommendations from our Python backend
        const response = await fetch('/api/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ movie_ids: movieIds })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Server error');
        }

        const recommendations = data.recommendations || [];

        if (recommendations.length === 0) {
            container.innerHTML = `<div class="empty-state">No recommendations found based on your selection.</div>`;
            return;
        }

        // Render placeholders or basic cards while fetching posters
        container.innerHTML = '';

        for (const rec of recommendations) {
            // Create card element
            const card = document.createElement('div');
            card.className = 'rec-card';

            // Initial HTML without poster
            card.innerHTML = `
                <img src="" alt="${rec.title}" class="rec-poster" style="display:none;" id="poster-${rec.id}">
                <div class="rec-poster" id="placeholder-${rec.id}" style="display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,0.2);">Loading...</div>
                <div class="rec-content">
                    <h3 class="rec-title">${rec.title}</h3>
                    <div class="rec-score">${rec.shared_connections} Shared Connections</div>
                </div>
            `;
            container.appendChild(card);

            // Fetch poster asynchronously
            fetch(`/api/poster?title=${encodeURIComponent(rec.title)}`)
                .then(res => res.json())
                .then(posterData => {
                    const imgEl = document.getElementById(`poster-${rec.id}`);
                    const phEl = document.getElementById(`placeholder-${rec.id}`);

                    if (posterData.poster) {
                        imgEl.src = posterData.poster;
                    } else {
                        // Fallback SVG
                        imgEl.src = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='300'><rect fill='%23334155' width='200' height='300'/></svg>`;
                    }
                    imgEl.style.display = 'block';
                    phEl.style.display = 'none';
                })
                .catch(err => {
                    const imgEl = document.getElementById(`poster-${rec.id}`);
                    const phEl = document.getElementById(`placeholder-${rec.id}`);
                    imgEl.src = `data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='300'><rect fill='%23334155' width='200' height='300'/></svg>`;
                    imgEl.style.display = 'block';
                    phEl.style.display = 'none';
                });
        }

    } catch (error) {
        console.error("Recommendation fetch failed:", error);
        container.innerHTML = `<div class="error-state">Failed to load recommendations: ${error.message}</div>`;
    }
});
