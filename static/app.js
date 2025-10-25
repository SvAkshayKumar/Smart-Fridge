document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    let allRecords = [];
    let inventoryChart;

    // --- DOM ELEMENT SELECTORS ---
    const logsContainer = document.getElementById('logs-container');
    const modal = document.getElementById('details-modal');
    const closeButton = document.getElementById('close-button');
    const imageContainer = document.getElementById('image-container');
    const inventoryContainer = document.getElementById('inventory-container');
    const recipesContainer = document.getElementById('recipes-container');
    const chartCtx = document.getElementById('inventoryChart')?.getContext('2d');

    // --- RENDER FUNCTIONS ---

    /**
     * Renders the list of the 5 latest logs on the main page.
     * @param {Array} records - Array of record objects.
     */
    const renderLogCards = (records) => {
        if (!records || records.length === 0) {
            logsContainer.innerHTML = `<p class="placeholder">No logs found.</p>`;
            return;
        }

        logsContainer.innerHTML = records.map(record => {
            const date = new Date(record.inserted_at);
            const formattedDate = `${date.toLocaleDateString()} at ${date.toLocaleTimeString()}`;
            return `
                <div class="log-card" data-id="${record.id}">
                    <h4>Log #${record.id}</h4>
                    <p>${formattedDate}</p>
                </div>
            `;
        }).join('');

        // Add click listeners to open the modal
        document.querySelectorAll('.log-card').forEach(card => {
            card.addEventListener('click', () => {
                const selectedId = parseInt(card.dataset.id);
                const selectedRecord = allRecords.find(r => r.id === selectedId);
                if (selectedRecord) {
                    renderDetailedView(selectedRecord);
                    modal.style.display = 'block';
                }
            });
        });
    };

    /**
     * Renders the detailed view inside the modal.
     * @param {object} record - The record object to display.
     */
    const renderDetailedView = (record) => {
        imageContainer.innerHTML = record.image_url ? `<img src="${record.image_url}" alt="Fridge scan #${record.id}" class="fridge-image">` : `<p class="placeholder">No image.</p>`;
        inventoryContainer.innerHTML = record.items?.length > 0 ? `<ul>${record.items.map(item => `<li>${item.quantity} x ${item.type}</li>`).join('')}</ul>` : `<p class="placeholder">No items detected.</p>`;
        recipesContainer.innerHTML = record.gemini_analysis?.recipeSuggestions?.length > 0 ? `<ul>${record.gemini_analysis.recipeSuggestions.map(r => `<li>${r}</li>`).join('')}</ul>` : `<p class="placeholder">No recipes.</p>`;
        renderInventoryChart(record.items || []);
    };

    /**
     * Renders or updates the inventory bar chart in the modal.
     * @param {Array} items - Array of item objects.
     */
    const renderInventoryChart = (items) => {
        if (!chartCtx) return;
        if (inventoryChart) inventoryChart.destroy();

        inventoryChart = new Chart(chartCtx, {
            type: 'bar',
            data: {
                labels: items.map(item => item.type),
                datasets: [{
                    label: 'Item Quantity',
                    data: items.map(item => item.quantity),
                    backgroundColor: 'rgba(187, 134, 252, 0.6)',
                    borderColor: 'rgba(187, 134, 252, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    };

    // --- API FETCH FUNCTIONS ---

    /**
     * Fetches the 5 latest records and updates the UI.
     */
    const fetchLatestRecords = async () => {
        try {
            const response = await fetch('/latest-records');
            const data = await response.json();
            
            // Simple check to see if data has changed
            if (JSON.stringify(data) !== JSON.stringify(allRecords)) {
                allRecords = data;
                renderLogCards(allRecords);
            }
        } catch (error) {
            console.error("Error fetching records:", error);
            logsContainer.innerHTML = `<p class="placeholder">Failed to load data.</p>`;
        }
    };

    // --- EVENT LISTENERS ---

    // Close the modal
    closeButton.onclick = () => modal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };

    // --- INITIALIZATION & DYNAMIC UPDATES ---
    const initializeDashboard = () => {
        fetchLatestRecords();
    };

    // Initial load
    initializeDashboard();

    // Set up polling for live updates every 10 seconds
    setInterval(fetchLatestRecords, 10000);
});