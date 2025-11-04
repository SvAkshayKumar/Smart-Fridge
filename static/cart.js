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
    let cart = {};
    let discountApplied = false;
    let isDeliveryFree = false;
    const DISCOUNT_CODE_VALUE = 99;
    const DELIVERY_FEE = 30;
    const FREE_DELIVERY_THRESHOLD = 150;

    // --- DOM ELEMENT SELECTORS ---
    const cartItemsContainer = document.getElementById('cart-items-container');
    const suggestionsContainer = document.getElementById('suggestions-container');
    const payButton = document.getElementById('pay-button');
    const deliveryStatusBanner = document.getElementById('delivery-status-banner');
    const applyCouponBtn = document.getElementById('apply-coupon-btn');
    const couponInput = document.getElementById('coupon-input');
    const couponMessage = document.getElementById('coupon-message');
    const confettiContainer = document.getElementById('confetti-container');
    const billDetailsCard = document.getElementById('bill-details-card');
    const couponCard = document.getElementById('coupon-card');
    const priceDropCard = document.getElementById('price-drop-card');
    const billItemTotalEl = document.getElementById('bill-item-total');
    const billDiscountRow = document.getElementById('bill-discount-row');
    const billDiscountAmountEl = document.getElementById('bill-discount-amount');
    const billDeliveryFeeEl = document.getElementById('bill-delivery-fee');
    const billGrandTotalEl = document.getElementById('bill-grand-total');
    const footerTotalPriceEl = document.getElementById('total-price-display');
    const addressDropdown = document.getElementById('address-dropdown');
    const toastOverlay = document.getElementById('toast-overlay');
    const toastText = document.getElementById('toast-text');

    const showToast = (message) => {
        toastText.textContent = message;
        toastOverlay.classList.remove('hidden');
        setTimeout(() => {
            toastOverlay.classList.add('hidden');
        }, 2500);
    };

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
        let hasSuggestions = false;
        for (const productKey in ALL_PRODUCTS) {
            const product = ALL_PRODUCTS[productKey];
            if (cart[product.id]) {
                itemTotal += product.price * cart[product.id];
            } else {
                hasSuggestions = true;
                const suggestionItemHTML = `<div class="suggestion-item" data-product-id="${product.id}"><img src="${product.image}" alt="${product.name}"><h4>${product.name}</h4><span class="suggestion-price">₹${product.price}</span><button class="btn-add">ADD</button></div>`;
                suggestionsContainer.innerHTML += suggestionItemHTML;
            }
        }
        priceDropCard.style.display = hasSuggestions ? 'block' : 'none';
        if (itemTotal === 0) {
            cartItemsContainer.innerHTML = '<p class="empty-cart-message">Your cart is empty!</p>';
            billDetailsCard.style.display = 'none';
            couponCard.style.display = 'none';
            deliveryStatusBanner.style.display = 'none';
            footerTotalPriceEl.textContent = '₹0.00';
            payButton.classList.add('disabled');
            return;
        }
        payButton.classList.remove('disabled');
        billDetailsCard.style.display = 'block';
        couponCard.style.display = 'block';
        Object.keys(cart).forEach(productId => {
            const productKey = Object.keys(ALL_PRODUCTS).find(key => ALL_PRODUCTS[key].id === productId);
            const product = ALL_PRODUCTS[productKey];
            const quantity = cart[productId];
            const cartItemHTML = `<div class="cart-item" data-product-id="${productId}"><img src="${product.image}" class="item-image" alt="${product.name}"><div class="item-info"><h4>${product.name}</h4><p>${product.description}</p><span class="item-price">₹${product.price}</span></div><div class="quantity-control"><button class="btn-decrease">-</button><span>${quantity}</span><button class="btn-increase">+</button></div></div>`;
            cartItemsContainer.innerHTML += cartItemHTML;
        });
        const deliveryFee = itemTotal >= FREE_DELIVERY_THRESHOLD ? 0 : DELIVERY_FEE;
        const actualDiscount = discountApplied ? Math.min(itemTotal, DISCOUNT_CODE_VALUE) : 0;
        const grandTotal = (itemTotal - actualDiscount) + deliveryFee;
        const newFreeDeliveryStatus = itemTotal >= FREE_DELIVERY_THRESHOLD;
        if (newFreeDeliveryStatus && !isDeliveryFree) {
            triggerConfetti();
            showToast("🎉 Free Delivery Applied!");
        }
        isDeliveryFree = newFreeDeliveryStatus;
        deliveryStatusBanner.style.display = 'block';
        if (newFreeDeliveryStatus) {
            deliveryStatusBanner.innerHTML = `<p>🎉 Free Delivery applied (orders over ₹${FREE_DELIVERY_THRESHOLD})</p>`;
            deliveryStatusBanner.classList.add('success');
        } else {
            const amountNeeded = FREE_DELIVERY_THRESHOLD - itemTotal;
            deliveryStatusBanner.innerHTML = `<p>Add ₹${amountNeeded.toFixed(2)} more for FREE delivery!</p>`;
            deliveryStatusBanner.classList.remove('success');
        }
        billItemTotalEl.textContent = `₹${itemTotal.toFixed(2)}`;
        billDiscountRow.style.display = (discountApplied && actualDiscount > 0) ? 'flex' : 'none';
        billDiscountAmountEl.textContent = `- ₹${actualDiscount.toFixed(2)}`;
        billDeliveryFeeEl.textContent = `₹${deliveryFee.toFixed(2)}`;
        billGrandTotalEl.textContent = `₹${grandTotal.toFixed(2)}`;
        footerTotalPriceEl.textContent = `₹${grandTotal.toFixed(2)}`;
    };
    
    document.querySelector('.app-container').addEventListener('click', (e) => {
        const productContainer = e.target.closest('[data-product-id]');
        if (!productContainer) return;
        const productId = productContainer.dataset.productId;
        if (e.target.matches('.btn-increase')) cart[productId] = (Number(cart[productId] || 0)) + 1;
        else if (e.target.matches('.btn-decrease')) {
            cart[productId]--;
            if (cart[productId] <= 0) delete cart[productId];
        } 
        else if (e.target.matches('.btn-add')) cart[productId] = 1;
        renderCart();
    });

    applyCouponBtn.addEventListener('click', () => {
        if (couponInput.value.trim().toUpperCase() !== 'SAVER99') {
            couponMessage.textContent = 'Invalid coupon code.';
            couponMessage.style.color = '#e0007a';
            couponCard.classList.add('shake-animation');
            couponCard.addEventListener('animationend', () => couponCard.classList.remove('shake-animation'), { once: true });
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
        showToast(`₹${amountSaved.toFixed(2)} Off Applied!`);
        couponMessage.textContent = `🎉 You saved ₹${amountSaved.toFixed(2)}!`;
        couponMessage.style.color = '#1aab2a';
        applyCouponBtn.style.display = 'none';
        couponInput.disabled = true;
        triggerConfetti();
        renderCart();
    });

    // --- UPDATED: Event listener for the pay button ---
    payButton.addEventListener('click', () => {
        let itemTotal = 0;
        Object.keys(cart).forEach(id => {
            const productKey = Object.keys(ALL_PRODUCTS).find(key => ALL_PRODUCTS[key].id === id);
            itemTotal += ALL_PRODUCTS[productKey].price * cart[id];
        });

        const deliveryFee = itemTotal >= FREE_DELIVERY_THRESHOLD ? 0 : DELIVERY_FEE;
        const actualDiscount = discountApplied ? Math.min(itemTotal, DISCOUNT_CODE_VALUE) : 0;
        const grandTotal = (itemTotal - actualDiscount) + deliveryFee;
        
        const selectedAddressText = addressDropdown.options[addressDropdown.selectedIndex].text;

        const orderDetails = {
            total: grandTotal.toFixed(2),
            address: selectedAddressText,
            items: cart
        };

        // Store the details in sessionStorage
        sessionStorage.setItem('orderDetails', JSON.stringify(orderDetails));
        sessionStorage.setItem('discountAmount', actualDiscount.toFixed(2));
        sessionStorage.setItem('deliveryCharge', deliveryFee.toFixed(2));

        // Navigate to the next page
        window.location.href = '/order-placed';
    });

    const initializeCartFromUrl = () => {
        const urlParams = new URLSearchParams(window.location.search);
        const suggestedItemsString = urlParams.get('items');
        if (suggestedItemsString) {
            try {
                const fridgeData = JSON.parse(decodeURIComponent(suggestedItemsString));
                if (fridgeData?.orderList?.length) {
                    const newCart = {};
                    fridgeData.orderList.forEach(item => {
                        const productName = Object.keys(item)[0];
                        const productDetails = ALL_PRODUCTS[productName];
                        if (productDetails) newCart[productDetails.id] = item[productName];
                    });
                    cart = newCart;
                    window.history.replaceState({}, document.title, window.location.pathname);
                }
            } catch (error) {
                console.error("Failed to parse suggestion data from URL:", error);
            }
        }
    };
    
    initializeCartFromUrl();
    renderCart();
});