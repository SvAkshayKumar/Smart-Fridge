document.addEventListener('DOMContentLoaded', () => {
    // --- MASTER PRODUCT LIST ---
    const ALL_PRODUCTS = {
        'onion': { id: 'onion', name: 'Fresh Onion', description: '1 Pack / 900-1000 gm', price: 72, originalPrice: 80, image: '/static/onion.jpeg' },
        'tomato': { id: 'tomato', name: 'Hybrid Tomato', description: '1 kg', price: 40, originalPrice: 55, image: '/static/tomato.jpeg' },
        'apple': { id: 'apple', name: 'Kashmiri Apple', description: '4 pieces', price: 110, originalPrice: 130, image: '/static/apple.jpeg' },
        'eggs': { id: 'eggs', name: 'Farm Fresh Eggs', description: 'Pack of 6', price: 50, originalPrice: 65, image: '/static/egg.jpeg' },
        'yogurt': { id: 'yogurt', name: 'Plain Curd/Yogurt', description: '400 gm Cup', price: 45, originalPrice: 50, image: '/static/yogurt.jpeg' },
    };

    // --- STATE MANAGEMENT ---
    let cart = {}; // Start with an empty cart
    let discountApplied = false;
    const DISCOUNT_CODE_VALUE = 99;
    const DELIVERY_FEE = 30;
    const FREE_DELIVERY_THRESHOLD = 150;

    // --- DOM ELEMENT SELECTORS ---
    const cartItemsContainer = document.getElementById('cart-items-container');
    const suggestionsContainer = document.getElementById('suggestions-container');
    const payButton = document.getElementById('pay-button');
    const freeDeliveryBanner = document.getElementById('free-delivery-banner');
    const applyCouponBtn = document.getElementById('apply-coupon-btn');
    const couponInput = document.getElementById('coupon-input');
    const couponMessage = document.getElementById('coupon-message');
    const confettiContainer = document.getElementById('confetti-container');
    const billDetailsCard = document.getElementById('bill-details-card');
    const couponCard = document.querySelector('.coupon-card');

    const billItemTotalEl = document.getElementById('bill-item-total');
    const billDiscountRow = document.getElementById('bill-discount-row');
    const billDiscountAmountEl = document.getElementById('bill-discount-amount');
    const billDeliveryFeeEl = document.getElementById('bill-delivery-fee');
    const billGrandTotalEl = document.getElementById('bill-grand-total');
    const footerTotalPriceEl = document.getElementById('total-price-display');

    const triggerConfetti = () => {
        confettiContainer.innerHTML = '';
        for (let i = 0; i < 50; i++) {
            const confetti = document.createElement('div');
            confetti.classList.add('confetti');
            confetti.style.left = `${Math.random() * 100}%`;
            confetti.style.animationDelay = `${Math.random() * 2}s`;
            confetti.style.backgroundColor = `hsl(${Math.random() * 360}, 100%, 50%)`;
            confettiContainer.appendChild(confetti);
        }
        confettiContainer.classList.add('animate');
        setTimeout(() => {
            confettiContainer.classList.remove('animate');
            confettiContainer.innerHTML = '';
        }, 5000);
    };

    const renderCart = () => {
        cartItemsContainer.innerHTML = '';
        suggestionsContainer.innerHTML = '';
        let itemTotal = 0;

        for (const productKey in ALL_PRODUCTS) {
            const product = ALL_PRODUCTS[productKey];
            const productId = product.id;
            
            if (cart[productId]) {
                const quantity = cart[productId];
                itemTotal += product.price * quantity;
            } else {
                 const suggestionItemHTML = `
                    <div class="suggestion-item" data-product-id="${productId}">
                        <img src="${product.image}" alt="${product.name}">
                        <h4>${product.name}</h4>
                        <span class="suggestion-price">₹${product.price}</span>
                        <button class="btn-add">ADD</button>
                    </div>`;
                suggestionsContainer.innerHTML += suggestionItemHTML;
            }
        }

        if (itemTotal === 0) {
            cartItemsContainer.innerHTML = '<p class="empty-cart-message">Your cart is empty!</p>';
            billDetailsCard.style.display = 'none';
            couponCard.style.display = 'none';
            freeDeliveryBanner.style.display = 'none';
            footerTotalPriceEl.textContent = '₹0.00';
            payButton.href = '/order-placed?total=0.00';
            return;
        }

        billDetailsCard.style.display = 'block';
        couponCard.style.display = 'block';

        Object.keys(cart).forEach(productId => {
            const productKey = Object.keys(ALL_PRODUCTS).find(key => ALL_PRODUCTS[key].id === productId);
            const product = ALL_PRODUCTS[productKey];
            const quantity = cart[productId];
            const cartItemHTML = `
                <div class="cart-item" data-product-id="${productId}">
                    <img src="${product.image}" class="item-image" alt="${product.name}">
                    <div class="item-info">
                        <h4>${product.name}</h4>
                        <p>${product.description}</p>
                        <span class="item-price">₹${product.price}</span>
                    </div>
                    <div class="quantity-control">
                        <button class="btn-decrease">-</button>
                        <span>${quantity}</span>
                        <button class="btn-increase">+</button>
                    </div>
                </div>`;
            cartItemsContainer.innerHTML += cartItemHTML;
        });

        const deliveryFee = itemTotal >= FREE_DELIVERY_THRESHOLD ? 0 : DELIVERY_FEE;
        const actualDiscount = discountApplied ? Math.min(itemTotal, DISCOUNT_CODE_VALUE) : 0;
        const subtotalAfterDiscount = itemTotal - actualDiscount;
        const grandTotal = subtotalAfterDiscount + deliveryFee;

        freeDeliveryBanner.style.display = itemTotal >= FREE_DELIVERY_THRESHOLD ? 'block' : 'none';
        billItemTotalEl.textContent = `₹${itemTotal.toFixed(2)}`;
        billDiscountRow.style.display = (discountApplied && actualDiscount > 0) ? 'flex' : 'none';
        billDiscountAmountEl.textContent = `- ₹${actualDiscount.toFixed(2)}`;
        billDeliveryFeeEl.textContent = `₹${deliveryFee.toFixed(2)}`;
        billGrandTotalEl.textContent = `₹${grandTotal.toFixed(2)}`;
        footerTotalPriceEl.textContent = `₹${grandTotal.toFixed(2)}`;
        payButton.href = `/order-placed?total=${grandTotal.toFixed(2)}`;
    };
    
    // --- EVENT LISTENERS ---
    document.querySelector('.app-container').addEventListener('click', (e) => {
        const target = e.target;
        const productContainer = target.closest('[data-product-id]');
        if (!productContainer) return;
        const productId = productContainer.dataset.productId;

        if (target.matches('.btn-increase')) cart[productId] = (cart[productId] || 0) + 1;
        else if (target.matches('.btn-decrease')) {
            cart[productId]--;
            if (cart[productId] <= 0) delete cart[productId];
        } 
        else if (target.matches('.btn-add')) cart[productId] = 1;
        
        renderCart();
    });

    applyCouponBtn.addEventListener('click', () => {
        if (couponInput.value.trim().toUpperCase() !== 'SAVER99') {
            couponMessage.textContent = 'Invalid coupon code.';
            couponMessage.style.color = '#e0007a';
            return;
        }
        if (discountApplied) {
            couponMessage.textContent = 'Discount already applied.';
            return;
        }

        discountApplied = true;
        let currentTotal = 0;
        Object.keys(cart).forEach(id => {
            const productKey = Object.keys(ALL_PRODUCTS).find(key => ALL_PRODUCTS[key].id === id);
            currentTotal += ALL_PRODUCTS[productKey].price * cart[id];
        });
        const amountSaved = Math.min(currentTotal, DISCOUNT_CODE_VALUE);

        couponMessage.textContent = `🎉 You saved ₹${amountSaved.toFixed(2)} on this order!`;
        couponMessage.style.color = '#1aab2a';
        applyCouponBtn.style.display = 'none';
        couponInput.disabled = true;
        
        triggerConfetti();
        renderCart();
    });

    // --- INITIALIZATION ---

    /**
     * MODIFIED: This function now checks for Gemini's shopping list in the URL,
     * populates the cart, and then cleans the URL to prevent re-adding on refresh.
     */
    const initializeCartFromUrl = () => {
        const urlParams = new URLSearchParams(window.location.search);
        const suggestedItemsString = urlParams.get('items');

        if (suggestedItemsString) {
            try {
                const fridgeData = JSON.parse(decodeURIComponent(suggestedItemsString));
                
                if (fridgeData && fridgeData.orderList && Array.isArray(fridgeData.orderList)) {
                    const newCart = {};
                    fridgeData.orderList.forEach(item => {
                        const productName = Object.keys(item)[0];
                        const quantity = item[productName];
                        const productDetails = ALL_PRODUCTS[productName];
                        
                        if (productDetails) {
                            newCart[productDetails.id] = quantity;
                        }
                    });
                    
                    cart = newCart;

                    // Clean the URL to prevent re-populating on refresh
                    window.history.replaceState({}, document.title, window.location.pathname);
                }
            } catch (error) {
                console.error("Failed to parse suggestion data from URL:", error);
            }
        }
    };
    
    // Run the initialization function first
    initializeCartFromUrl();
    
    // Then, render the cart with either the pre-filled or empty data
    renderCart();
});