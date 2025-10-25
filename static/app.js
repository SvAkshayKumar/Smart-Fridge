document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    let allRecords = [];
    let currentRecord = null; // Store the currently viewed record

    // --- DOM ELEMENT SELECTORS ---
    const logsContainer = document.getElementById('logs-container');
    const modal = document.getElementById('details-modal');
    const closeButton = document.getElementById('close-button');
    
    // Modal Content Holders
    const imageContainer = document.getElementById('image-container');
    const inventoryContainer = document.getElementById('inventory-container');
    const recipesContainer = document.getElementById('recipes-container');
    const recipeStepsContainer = document.getElementById('recipe-steps-container');

    // --- RENDER FUNCTIONS ---

    /**
     * Renders the list of the latest logs on the main page.
     */
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

    /**
     * Renders the entire content of the modal for a given record.
     */
    const renderModalContent = (record) => {
        // 1. Render Photo
        imageContainer.innerHTML = record.image_url 
            ? `<img src="${record.image_url}" alt="Fridge scan" class="fridge-image">` 
            : `<p class="placeholder">No image available.</p>`;

        // 2. Render Inventory
        inventoryContainer.innerHTML = record.items?.length > 0 
            ? `<ul>${record.items.map(item => `<li>${item.quantity} x ${item.type}</li>`).join('')}</ul>` 
            : `<p class="placeholder">No items detected.</p>`;

        // 3. Render Recipe Suggestions
        // IMPORTANT: Assumes gemini_analysis.recipeSuggestions is an array of objects like {name: '...', steps: ['...', '...']}
        if (record.gemini_analysis?.recipeSuggestions?.length > 0) {
            recipesContainer.innerHTML = `<ul class="recipes-list">${record.gemini_analysis.recipeSuggestions.map(recipe => 
                `<li class="recipe-item" data-recipe-name="${recipe.name}">${recipe.name}</li>`
            ).join('')}</ul>`;
        } else {
            recipesContainer.innerHTML = `<p class="placeholder">No suggestions available.</p>`;
        }
        
        // 4. Clear and reset the recipe steps section
        recipeStepsContainer.innerHTML = `<p class="placeholder">Click on a recipe suggestion above to see the steps.</p>`;
    };

    /**
     * Renders the detailed steps for a single recipe in the modal's bottom section.
     */
    const renderRecipeSteps = (recipe) => {
        if (!recipe || !recipe.steps) {
            recipeStepsContainer.innerHTML = `<p class="placeholder">Recipe steps not found.</p>`;
            return;
        }

        const stepsHtml = recipe.steps.map(step => `<li>${step}</li>`).join('');
        recipeStepsContainer.innerHTML = `
            <h4>Steps for ${recipe.name}</h4>
            <ol class="steps-list">${stepsHtml}</ol>
        `;
    };

    // --- API FETCH FUNCTION ---
    const fetchLatestRecords = async () => {
        try {
            // This is a mock fetch. Replace with your actual API endpoint.
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

    // --- EVENT LISTENERS ---

    // Listener for clicking a recipe suggestion (uses event delegation)
    recipesContainer.addEventListener('click', (e) => {
        const recipeItem = e.target.closest('.recipe-item');
        if (!recipeItem) return;

        const recipeName = recipeItem.dataset.recipeName;
        const recipeData = currentRecord.gemini_analysis.recipeSuggestions.find(r => r.name === recipeName);
        
        if (recipeData) {
            // Highlight the selected recipe
            document.querySelectorAll('.recipe-item').forEach(item => item.classList.remove('active'));
            recipeItem.classList.add('active');
            
            renderRecipeSteps(recipeData);
        }
    });

    // Listeners for closing the modal
    closeButton.onclick = () => modal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };

    // --- INITIALIZATION ---
    fetchLatestRecords();
    setInterval(fetchLatestRecords, 10000); // Dynamic updates
});