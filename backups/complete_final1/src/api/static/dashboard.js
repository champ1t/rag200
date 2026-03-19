// Dashboard JavaScript - Real-time stats fetching and display

const API_BASE = 'http://localhost:8000';
const REFRESH_INTERVAL = 5000; // 5 seconds

// Fetch and update dashboard data
async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');

        const data = await response.json();
        updateDashboard(data);

        // Update last refresh time
        document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString('th-TH');
    } catch (error) {
        console.error('Error fetching stats:', error);
        document.getElementById('lastUpdate').textContent = 'Error';
    }
}

// Update dashboard with new data
function updateDashboard(data) {
    const stats = data.query_stats || {};
    const totalQueries = stats.total_queries || 0;
    const articleServed = stats.article_served_queries || 0;
    const blocked = stats.blocked_queries || 0;
    const missing = stats.missing_article_queries || 0;

    // Update stat cards
    document.getElementById('totalQueries').textContent = totalQueries.toLocaleString();

    const successRate = totalQueries > 0 ? ((articleServed / totalQueries) * 100).toFixed(1) : '0.0';
    document.getElementById('successRate').textContent = successRate + '%';

    const errorRate = totalQueries > 0 ? (((blocked + missing) / totalQueries) * 100).toFixed(1) : '0.0';
    document.getElementById('errorRate').textContent = errorRate + '%';

    document.getElementById('activeTeams').textContent = data.teams || 0;

    // Update intents table
    updateIntentsTable(stats.intents || {}, totalQueries);

    // Update recent queries table
    updateRecentQueries(data.recent_queries || []);
}

// Update top intents table
function updateIntentsTable(intents, total) {
    const tbody = document.querySelector('#intentsTable tbody');

    if (Object.keys(intents).length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" class="loading">No data available</td></tr>';
        return;
    }

    // Sort by count descending
    const sortedIntents = Object.entries(intents)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10); // Top 10

    tbody.innerHTML = sortedIntents.map(([intent, count]) => {
        const percentage = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';
        return `
            <tr>
                <td><strong>${intent}</strong></td>
                <td>${count}</td>
                <td>${percentage}%</td>
            </tr>
        `;
    }).join('');
}

// Update recent queries table
function updateRecentQueries(queries) {
    const tbody = document.querySelector('#recentQueriesTable tbody');

    if (queries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading">No recent queries</td></tr>';
        return;
    }

    tbody.innerHTML = queries.reverse().map(entry => {
        const timestamp = new Date(entry.timestamp * 1000).toLocaleTimeString('th-TH');
        const query = entry.query || '--';
        const intent = entry.intent || '--';
        const result = entry.result || '--';

        // Badge color based on result
        let badgeClass = 'badge-success';
        if (result === 'BLOCK' || result === 'MISSING') {
            badgeClass = 'badge-error';
        } else if (result.includes('warn')) {
            badgeClass = 'badge-warning';
        }

        return `
            <tr>
                <td class="timestamp">${timestamp}</td>
                <td>${query}</td>
                <td>${intent}</td>
                <td><span class="badge ${badgeClass}">${result}</span></td>
            </tr>
        `;
    }).join('');
}

// Initialize auto-refresh
function startAutoRefresh() {
    // Initial fetch
    fetchStats();

    // Auto-refresh every 5 seconds
    setInterval(fetchStats, REFRESH_INTERVAL);
}

// Start when page loads
document.addEventListener('DOMContentLoaded', startAutoRefresh);
