document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    let allRecords = []; // To store the latest 5 records
    let currentRecordId = null; // To track the latest record for updates
    let inventoryChart; // To hold the Chart.js instance

    // --- DOM ELEMENT SELECTORS ---
    const carouselContainer = document.getElementById('records-carousel');
    const imageContainer = document.getElementById('image-container');
    const inventoryContainer = document.getElementById('inventory-container');
    const recipesContainer = document.getElementById('recipes-container');
    const chartCtx = document.getElementById('inventoryChart')?.getContext('2d');

    // Notification Elements
    const bellIcon = document.getElementById('bell-icon');
    const notificationBadge = document.getElementById('notification-badge');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationArea = document.getElementById('notification-area');

    // --- RENDER FUNCTIONS ---

    /**
     * Renders the top carousel of 5 record cards.
     * @param {Array} records - Array of record objects from the server.
     */
    const renderRecordCards = (records) => {
        if (!records || records.length === 0) {
            carouselContainer.innerHTML = `<p class="placeholder">No scans found yet. Your fridge will send data soon.</p>`;
            return;
        }

        carouselContainer.innerHTML = records.map(record => {
            const date = new Date(record.inserted_at);
            const formattedDate = `${date.toLocaleDateString()} at ${date.toLocaleTimeString()}`;
            return `
                <div class="record-card" data-id="${record.id}">
                    <img src="${record.image_url}" alt="Fridge scan" class="record-card-img">
                    <div class="record-card-info">
                        <h4>Scan #${record.id}</h4>
                        <p>${formattedDate}</p>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add click listeners to each new card
        document.querySelectorAll('.record-card').forEach(card => {
            card.addEventListener('click', () => {
                const selectedId = parseInt(card.dataset.id);
                const selectedRecord = allRecords.find(r => r.id === selectedId);
                if (selectedRecord) {
                    renderDetailedView(selectedRecord);
                }
            });
        });
    };

    /**
     * Renders the detailed view (image, inventory, recipes, chart) for a single record.
     * @param {object} record - The record object to display.
     */
    const renderDetailedView = (record) => {
        // Highlight the active card
        document.querySelectorAll('.record-card').forEach(card => {
            card.classList.toggle('active', parseInt(card.dataset.id) === record.id);
        });

        // 1. Populate Image
        if (record?.image_url) {
            imageContainer.innerHTML = `<img src="${record.image_url}" alt="Fridge content scan #${record.id}" class="fridge-image">`;
        } else {
            imageContainer.innerHTML = `<p class="placeholder">No image available for this scan.</p>`;
        }

        // 2. Populate Inventory List
        if (record?.items?.length > 0) {
            const itemsHtml = record.items.map(item => `<li>${item.quantity} x ${item.type}</li>`).join('');
            inventoryContainer.innerHTML = `<ul class="item-list">${itemsHtml}</ul>`;
        } else {
            inventoryContainer.innerHTML = `<p class="placeholder">No items were detected in this scan.</p>`;
        }

        // 3. Populate Gemini's Recipes
        if (record?.gemini_analysis?.recipeSuggestions?.length > 0) {
            const recipesHtml = record.gemini_analysis.recipeSuggestions.map(r => `<li>${r}</li>`).join('');
            recipesContainer.innerHTML = `<ul class="recipes-list">${recipesHtml}</ul>`;
        } else {
            recipesContainer.innerHTML = `<p class="placeholder">No recipe suggestions were generated for this inventory.</p>`;
        }

        // 4. Render the Analysis Chart
        renderInventoryChart(record.items || []);
    };

    /**
     * Renders or updates the inventory bar chart.
     * @param {Array} items - Array of item objects.
     */
    const renderInventoryChart = (items) => {
        if (!chartCtx) return;

        const labels = items.map(item => item.type);
        const data = items.map(item => item.quantity);

        if (inventoryChart) {
            inventoryChart.destroy(); // Destroy old chart to prevent conflicts
        }

        inventoryChart = new Chart(chartCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Item Quantity',
                    data: data,
                    backgroundColor: 'rgba(187, 134, 252, 0.6)',
                    borderColor: 'rgba(187, 134, 252, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, ticks: { color: '#a0a0a0' }, grid: { color: '#333' } },
                    x: { ticks: { color: '#a0a0a0' }, grid: { color: '#333' } }
                },
                plugins: { legend: { labels: { color: '#e0e0e0' } } }
            }
        });
    };

    /**
     * Renders the notification panel.
     * @param {Array} notifications - Array of notification objects.
     */
    const renderNotifications = (notifications) => {
        const count = notifications.length;
        notificationBadge.textContent = count;
        notificationBadge.style.display = count > 0 ? 'flex' : 'none';
        
        if (count === 0) {
            notificationPanel.innerHTML = '<div class="notification-item"><p>No new notifications.</p></div>';
            return;
        }

        notificationPanel.innerHTML = notifications.map(notif => `
            <div class="notification-item" data-id="${notif.id}" data-type="${notif.type}" data-payload='${JSON.stringify(notif.payload)}'>
                <h4>${notif.title}</h4>
                <p>${notif.message || ''}</p>
                <div class="notification-actions">
                    <button class="mark-read-btn" data-id="${notif.id}">Mark as Read</button>
                </div>
            </div>
        `).join('');
    };

    // --- API FETCH FUNCTIONS ---

    /**
     * Fetches the 5 latest records and updates the UI.
     */
    const fetchLatestRecords = async () => {
        try {
            const response = await fetch('/latest-records');
            const data = await response.json();
            
            if (data.length === 0) return;

            // Check if there's a new record since the last fetch
            const newLatestId = data.id;
            if (newLatestId !== currentRecordId) {
                console.log("New data detected. Updating dashboard.");
                currentRecordId = newLatestId;
                allRecords = data;
                
                renderRecordCards(allRecords);
                renderDetailedView(allRecords); // Display the newest record by default
            }
        } catch (error) {
            console.error("Error fetching latest records:", error);
        }
    };

    const fetchNotifications = async () => {
        try {
            const response = await fetch('/notifications');
            const data = await response.json();
            renderNotifications(data);
        } catch (error) {
            console.error("Error fetching notifications:", error);
        }
    };

    const markNotificationAsRead = async (id) => {
        try {
            await fetch('/notifications/mark-as-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            fetchNotifications(); // Refresh notifications after marking one as read
        } catch (error) {
            console.error("Error marking notification as read:", error);
        }
    };

    // --- EVENT LISTENERS ---

    bellIcon.addEventListener('click', () => {
        notificationPanel.style.display = notificationPanel.style.display === 'block' ? 'none' : 'block';
    });

    notificationPanel.addEventListener('click', (e) => {
        const target = e.target;
        if (target.classList.contains('mark-read-btn')) {
            e.stopPropagation();
            markNotificationAsRead(target.dataset.id);
        } else {
            const item = target.closest('.notification-item');
            if (item && item.dataset.type === 'order_suggestion') {
                localStorage.setItem('fridgeData', item.dataset.payload);
                window.location.href = '/cart';
            }
        }
    });

    document.addEventListener('click', (e) => {
        if (!notificationArea.contains(e.target)) {
            notificationPanel.style.display = 'none';
        }
    });

    // --- INITIALIZATION & DYNAMIC UPDATES ---
    const initializeDashboard = () => {
        fetchLatestRecords();
        fetchNotifications();
    };

    // Initial load
    initializeDashboard();

    // Set up polling for live updates every 15 seconds (15000 milliseconds)
    setInterval(() => {
        console.log("Checking for updates...");
        fetchLatestRecords();
        fetchNotifications();
    }, 15000);
});