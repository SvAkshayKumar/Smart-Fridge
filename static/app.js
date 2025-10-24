document.addEventListener("DOMContentLoaded", () => {
    // Only run this script on the cart page
    if (window.location.pathname !== '/cart') {
        return;
    }

    const cartContainer = document.getElementById('cart-items-container');
    const suggestionsContainer = document.getElementById('suggestions-container');
    const payButton = document.getElementById('pay-button');
    let cart = [];

    // --- RENDER FUNCTIONS ---

    const renderCart = () => {
        cartContainer.innerHTML = ''; // Clear existing items
        if (cart.length === 0) {
            cartContainer.innerHTML = '<p>Your cart is empty.</p>';
        } else {
            cart.forEach((item, index) => {
                const itemElement = document.createElement('div');
                itemElement.className = 'cart-item';
                itemElement.innerHTML = `
                    <img src="https://via.placeholder.com/100" alt="${item.name}">
                    <div class="item-details">
                        <h5>${item.name}</h5>
                        <p>${item.packInfo}</p>
                    </div>
                    <div class="quantity-control">
                        <button class="quantity-btn" data-index="${index}" data-action="decrease">-</button>
                        <span>${item.quantity}</span>
                        <button class="quantity-btn" data-index="${index}" data-action="increase">+</button>
                    </div>
                    <div class="item-pricing">
                        <div class="price">₹${(item.price * item.quantity).toFixed(2)}</div>
                        <div class="original-price">₹${(item.originalPrice * item.quantity).toFixed(2)}</div>
                    </div>
                `;
                cartContainer.appendChild(itemElement);
            });
        }
        updateTotal();
    };
    
    const renderSuggestions = (suggestions) => {
        suggestionsContainer.innerHTML = '';
        suggestions.forEach(item => {
            const suggestionElement = document.createElement('div');
            suggestionElement.className = 'suggestion-item';
            suggestionElement.innerHTML = `
                <img src="https://via.placeholder.com/150" alt="${item.name}">
                <div class="name">${item.name}</div>
                <div class="prices">
                    <strong>₹${item.price}</strong>
                    <span class="original-price">₹${item.originalPrice}</span>
                </div>
                <button class="add-btn" data-name="${item.name}" data-packinfo="${item.packInfo}" data-price="${item.price}" data-originalprice="${item.originalPrice}">ADD</button>
            `;
            suggestionsContainer.appendChild(suggestionElement);
        });
    };

    // --- HELPER FUNCTIONS ---

    const updateTotal = () => {
        const total = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        payButton.textContent = `Click to Pay ₹${total.toFixed(2)}`;
    };

    const updateQuantity = (index, action) => {
        if (action === 'increase') {
            cart[index].quantity++;
        } else if (action === 'decrease') {
            cart[index].quantity--;
            if (cart[index].quantity <= 0) {
                // Remove item if quantity is 0 or less
                cart.splice(index, 1);
            }
        }
        renderCart();
    };

    const addItemToCart = (newItem) => {
        // Check if item already exists in cart
        const existingItemIndex = cart.findIndex(item => item.name === newItem.name);
        if (existingItemIndex > -1) {
            cart[existingItemIndex].quantity++;
        } else {
            cart.push({ ...newItem, quantity: 1 });
        }
        renderCart();
    };

    // --- EVENT LISTENERS ---

    cartContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('quantity-btn')) {
            const index = e.target.dataset.index;
            const action = e.target.dataset.action;
            updateQuantity(index, action);
        }
    });

    suggestionsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('add-btn')) {
            const { name, packinfo, price, originalprice } = e.target.dataset;
            const newItem = {
                name,
                packInfo: packinfo,
                price: parseFloat(price),
                originalPrice: parseFloat(originalprice)
            };
            addItemToCart(newItem);
        }
    });

    // --- INITIALIZATION ---

    const init = () => {
        const dataString = localStorage.getItem('fridgeData');
        if (!dataString) {
            console.error("No fridge data found in localStorage.");
            cartContainer.innerHTML = '<p>Could not load cart data. Please go back to the dashboard.</p>';
            return;
        }

        const data = JSON.parse(dataString);
        // Initialize the cart with a quantity of 1 for each suggested item
        cart = data.orderList.map(item => ({...item, quantity: 1 }));
        
        renderCart();
        renderSuggestions(data.suggestedAddons);
    };

    init();
});