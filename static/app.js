document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    let allRecords = [];
    let currentRecord = null;

    // --- DOM ELEMENT SELECTORS ---
    const logsContainer = document.getElementById('logs-container');
    const modal = document.getElementById('details-modal');
    const closeButton = document.getElementById('close-button');

    // Modal Content Holders
    const imageContainer = document.getElementById('image-container');
    const inventoryContainer = document.getElementById('inventory-container');
    const recipesContainer = document.getElementById('recipes-container');
    const recipeStepsContainer = document.getElementById('recipe-steps-container');

    // Notification Elements
    const bellIcon = document.getElementById('bell-icon');
    const notificationBadge = document.getElementById('notification-badge');
    const notificationPanel = document.getElementById('notification-panel');
    const notificationArea = document.getElementById('notification-area');

    // --- RENDER FUNCTIONS ---

    const renderLogCards = (records) => {
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

        document.querySelectorAll('.log-card').forEach(card => {
            card.addEventListener('click', () => {
                const selectedId = parseInt(card.dataset.id);
                currentRecord = allRecords.find(r => r.id === selectedId);
                if (currentRecord) {
                    renderModalContent(currentRecord);
                    modal.style.display = 'block';
                }
            });
        });
    };

    const renderModalContent = (record) => {
        imageContainer.innerHTML = record.image_url ? `<img src="${record.image_url}" alt="Fridge scan" class="fridge-image">` : `<p class="placeholder">No image available.</p>`;
        inventoryContainer.innerHTML = record.items?.length > 0 ? `<ul>${record.items.map(item => `<li>${item.quantity} x ${item.type}</li>`).join('')}</ul>` : `<p class="placeholder">No items detected.</p>`;
        
        if (record.gemini_analysis?.recipeSuggestions?.length > 0) {
            recipesContainer.innerHTML = `<ul class="recipes-list">${record.gemini_analysis.recipeSuggestions.map(recipe => 
                `<li class="recipe-item" data-recipe-name="${recipe}">${recipe}</li>`
            ).join('')}</ul>`;
        } else {
            recipesContainer.innerHTML = `<p class="placeholder">No suggestions available.</p>`;
        }
        
        recipeStepsContainer.innerHTML = `<p class="placeholder">Click on a recipe suggestion above to see the steps.</p>`;
    };

    const renderRecipeSteps = (recipe) => {
        if (!recipe || !recipe.steps || recipe.steps.length === 0) {
            recipeStepsContainer.innerHTML = `<p class="placeholder">Recipe steps not found or are empty.</p>`;
            return;
        }
        const stepsHtml = recipe.steps.map(step => `<li>${step}</li>`).join('');
        recipeStepsContainer.innerHTML = `<h4>Steps for ${recipe.name}</h4><ol class="steps-list">${stepsHtml}</ol>`;
    };

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

    const fetchLatestRecords = async () => {
        try {
            const response = await fetch('/latest-records');
            const data = await response.json();
            if (JSON.stringify(data) !== JSON.stringify(allRecords)) {
                allRecords = data;
                renderLogCards(allRecords);
            }
        } catch (error) {
            console.error("Error fetching records:", error);
            logsContainer.innerHTML = `<p class="placeholder">Failed to load data.</p>`;
        }
    };

    /**
     * NEW: Fetches recipe steps from the server.
     */
    const fetchRecipeSteps = async (recipeName) => {
        try {
            const response = await fetch('/get_recipe_steps', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ recipe_name: recipeName })
            });

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            
            const data = await response.json();
            return data.steps; // Assuming the server returns { "steps": [...] }
        } catch (error) {
            console.error("Error fetching recipe steps:", error);
            // Display an error in the steps container
            recipeStepsContainer.innerHTML = `<p class="placeholder">Failed to fetch recipe steps. Please try again.</p>`;
            return null;
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
            fetchNotifications(); // Refresh notifications
        } catch (error)
        {
            console.error("Error marking notification as read:", error);
        }
    };

    // --- EVENT LISTENERS ---

    /**
     * MODIFIED: This listener now handles fetching steps and showing a loading animation.
     */
    recipesContainer.addEventListener('click', async (e) => {
        const recipeItem = e.target.closest('.recipe-item');
        if (!recipeItem) return;

        const recipeName = recipeItem.dataset.recipeName;

        // Highlight the selected recipe
        document.querySelectorAll('.recipe-item').forEach(item => item.classList.remove('active'));
        recipeItem.classList.add('active');

        // Show loading animation
        recipeStepsContainer.innerHTML = `
            <div class="loader-container">
                <div class="loader"></div>
                <p>Fetching steps for ${recipeName}, one moment...</p>
            </div>
        `;

        // Fetch the recipe steps from the backend
        const steps = await fetchRecipeSteps(recipeName);

        // If the fetch was successful, render the steps
        if (steps) {
            renderRecipeSteps({ name: recipeName, steps: steps });
        }
    });

    closeButton.onclick = () => modal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };

    bellIcon.addEventListener('click', () => {
        notificationPanel.style.display = notificationPanel.style.display === 'block' ? 'none' : 'block';
    });

    notificationPanel.addEventListener('click', (e) => {
        const target = e.target;
        if (target.classList.contains('mark-read-btn')) {
            e.stopPropagation();
            const notificationId = target.dataset.id;
            markNotificationAsRead(notificationId);
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

    initializeDashboard();
    setInterval(() => {
        fetchLatestRecords();
        fetchNotifications();
    }, 10000);
});