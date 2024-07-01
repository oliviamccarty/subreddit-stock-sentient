let currentSort = { column: 'score', order: 'desc' };

async function fetchData() {
    document.getElementById('loading').style.display = 'block';
    const minSentiment = document.getElementById('minSentiment').value;
    const maxSentiment = document.getElementById('maxSentiment').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const numPosts = document.getElementById('numPosts').value;

    try {
        const response = await fetch(`/api/tickers?minSentiment=${minSentiment}&maxSentiment=${maxSentiment}&startDate=${startDate}&endDate=${endDate}&numPosts=${numPosts}`);
        const data = await response.json();
        document.getElementById('loading').style.display = 'none';

        renderTable(data);
    } catch (error) {
        console.error('Error fetching data:', error);
        document.getElementById('loading').style.display = 'none';
    }
}

function sortData(data, column, order) {
    return data.sort((a, b) => {
        const aValue = parseFloat(a[column]);
        const bValue = parseFloat(b[column]);

        if (order === 'asc') {
            return aValue - bValue;
        } else {
            return bValue - aValue;
        }
    });
}

function renderTable(data) {
    data = sortData(data, currentSort.column, currentSort.order);

    const tableBody = document.querySelector('#tickerTable tbody');
    tableBody.innerHTML = '';
    data.forEach((row, index) => {
        const sentimentClass = getSentimentClass(row.average_sentiment);
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${new Date(row.date).toISOString().split('T')[0]}</td>
            <td><a href="https://finance.yahoo.com/quote/${row.ticker}" target="_blank" class="ticker-link">${row.ticker}</a></td>
            <td>${row.subreddit}</td>
            <td>${row.title_sentiment}</td>
            <td>${row.body_sentiment}</td>
            <td class="${sentimentClass}">${row.average_sentiment}</td>
            <td>${row.score}</td>
            <td><button class="view-post-btn" onclick="togglePostDetails(${index}, this)">&#9654; View Post</button></td>
        `;
        const detailsRow = document.createElement('tr');
        detailsRow.className = 'post-details-row';
        detailsRow.innerHTML = `
            <td colspan="8">
                <div class="post-details" id="post-details-${index}">
                    <strong>Title:</strong> ${row.title || 'N/A'}<br>
                    <strong>Posted by:</strong> ${row.author || 'N/A'}<br>
                    <div class="post-body"><strong>Body:</strong> ${row.body || 'N/A'}</div>
                    <a href="https://www.reddit.com${row.url}" target="_blank" class="original-post-link">View Original Post</a>
                </div>
            </td>
        `;
        detailsRow.style.display = 'none';
        tableBody.appendChild(tr);
        tableBody.appendChild(detailsRow);
    });
}

function getSentimentClass(sentiment) {
    if (sentiment > 0) {
        return 'positive-sentiment';
    } else if (sentiment < 0) {
        return 'negative-sentiment';
    } else {
        return 'neutral-sentiment';
    }
}

function togglePostDetails(index, button) {
    const detailsRow = document.getElementById(`post-details-${index}`).parentElement.parentElement;
    if (detailsRow.style.display === 'none') {
        detailsRow.style.display = '';
        button.innerHTML = '&#9660; Hide Post';
    } else {
        detailsRow.style.display = 'none';
        button.innerHTML = '&#9654; View Post';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('startDate').value = today;
    document.getElementById('endDate').value = today;
    document.getElementById('endDate').max = today;

    document.getElementById('loading').style.display = 'none'; // Ensure the loading spinner is hidden on page load
    document.getElementById('sortOption').addEventListener('change', (event) => {
        currentSort = { column: 'score', order: event.target.value };
        fetchData();
    });

    // Initialize Tippy.js tooltips
    tippy('[data-tippy-content]', {
        allowHTML: true,
        interactive: true,
        placement: 'top',
    });
});
