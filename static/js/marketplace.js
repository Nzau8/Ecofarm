// Handle infinite scroll
let loading = false;
let page = 1;
const productGrid = document.querySelector('.product-grid');

// Debounce function to limit rate of function calls
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Load more products when scrolling
function loadMoreProducts() {
    if (loading) return;
    
    const scrollPosition = window.innerHeight + window.pageYOffset;
    const pageHeight = document.documentElement.scrollHeight;
    
    if (scrollPosition >= pageHeight - 1000) {
        loading = true;
        page++;
        
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('page', page);
        
        fetch(currentUrl)
            .then(response => response.text())
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newProducts = doc.querySelector('.product-grid').innerHTML;
                
                productGrid.insertAdjacentHTML('beforeend', newProducts);
                loading = false;
                
                initializeProductCards();
            });
    }
}

// Initialize product cards
function initializeProductCards() {
    document.querySelectorAll('.product-card').forEach(card => {
        // Quick view functionality
        card.querySelector('.quick-view-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            const productId = card.dataset.productId;
            showQuickView(productId);
        });

        // Add to cart functionality
        card.querySelector('.add-to-cart-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            const productId = card.dataset.productId;
            addToCart(productId, 1);
        });

        // Add to wishlist functionality
        card.querySelector('.add-to-wishlist-btn')?.addEventListener('click', (e) => {
            e.preventDefault();
            const productId = card.dataset.productId;
            toggleWishlist(productId);
        });
    });
}

// Quick view modal functionality
function showQuickView(productId) {
    fetch(`/product/${productId}/quick-view/`)
        .then(response => response.text())
        .then(html => {
            const modal = document.getElementById('quickViewModal');
            modal.querySelector('.modal-body').innerHTML = html;
            new bootstrap.Modal(modal).show();
            
            initializeVariantSelection(modal);
            initializeQuantityInput(modal);
        });
}

// Handle variant selection
function initializeVariantSelection(container) {
    const variantCards = container.querySelectorAll('.variant-card');
    const variantInput = container.querySelector('#selectedVariantId');
    
    variantCards.forEach(card => {
        card.addEventListener('click', () => {
            variantCards.forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
            variantInput.value = card.dataset.variantId;
            
            updatePrice(container, card.dataset.price);
            updateStock(container, card.dataset.stock);
        });
    });
}

// Handle quantity input
function initializeQuantityInput(container) {
    const quantityInput = container.querySelector('.quantity-input');
    const decreaseBtn = container.querySelector('.decrease-quantity');
    const increaseBtn = container.querySelector('.increase-quantity');
    
    if (!quantityInput) return;
    
    const minOrder = parseInt(quantityInput.min) || 1;
    const maxOrder = parseInt(quantityInput.max) || 99999;
    
    decreaseBtn?.addEventListener('click', () => {
        let value = parseInt(quantityInput.value);
        if (value > minOrder) {
            quantityInput.value = value - 1;
            updateSubtotal(container);
        }
    });
    
    increaseBtn?.addEventListener('click', () => {
        let value = parseInt(quantityInput.value);
        if (value < maxOrder) {
            quantityInput.value = value + 1;
            updateSubtotal(container);
        }
    });
    
    quantityInput.addEventListener('change', () => {
        let value = parseInt(quantityInput.value);
        if (value < minOrder) quantityInput.value = minOrder;
        if (value > maxOrder) quantityInput.value = maxOrder;
        updateSubtotal(container);
    });
}

// Update price display
function updatePrice(container, price) {
    const priceElement = container.querySelector('.product-price');
    if (priceElement) {
        priceElement.textContent = `KES ${parseFloat(price).toFixed(2)}`;
        priceElement.dataset.price = price;
        updateSubtotal(container);
    }
}

// Update stock status
function updateStock(container, stock) {
    const stockElement = container.querySelector('.stock-status');
    if (stockElement) {
        stockElement.textContent = `${stock} available`;
        
        const addToCartBtn = container.querySelector('.add-to-cart-btn');
        if (addToCartBtn) {
            addToCartBtn.disabled = stock <= 0;
        }
    }
}

// Update subtotal calculation
function updateSubtotal(container) {
    const quantity = parseInt(container.querySelector('.quantity-input').value);
    const price = parseFloat(container.querySelector('.product-price').dataset.price);
    const subtotalElement = container.querySelector('.subtotal');
    
    if (subtotalElement && !isNaN(quantity) && !isNaN(price)) {
        const subtotal = quantity * price;
        subtotalElement.textContent = `KES ${subtotal.toFixed(2)}`;
    }
}

// Validate quantity before adding to cart
function validateQuantity(productId, quantity, min, max) {
    const qty = parseInt(quantity);
    if (isNaN(qty) || qty < min || qty > max) {
        showToast(`Please enter a quantity between ${min} and ${max}`, 'error');
        return false;
    }
    return true;
}

// Enhanced addToCart function
function addToCart(productId, quantity) {
    const minQty = document.querySelector(`#quantity-${productId}`).getAttribute('min') || 1;
    const maxQty = document.querySelector(`#quantity-${productId}`).getAttribute('max');
    
    if (!validateQuantity(productId, quantity, minQty, maxQty)) {
        return;
    }

    const data = new FormData();
    data.append('product_id', productId);
    data.append('quantity', quantity);
    
    fetch('/add-to-cart/', {
        method: 'POST',
        body: data,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('Product added to cart successfully!', 'success');
            updateCartCount(data.cart_count);
        } else {
            showToast(data.message || 'Error adding product to cart', 'error');
        }
    });
}

// Toggle wishlist functionality
function toggleWishlist(productId) {
    const data = new FormData();
    data.append('product_id', productId);
    
    fetch('/toggle-wishlist/', {
        method: 'POST',
        body: data,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const btn = document.querySelector(`.add-to-wishlist-btn[data-product-id="${productId}"]`);
            btn.classList.toggle('active');
            showToast(data.message, 'success');
        } else {
            showToast(data.message || 'Error updating wishlist', 'error');
        }
    });
}

// Show toast notifications
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    const container = document.getElementById('toast-container') || document.body;
    container.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

// Update cart count in header
function updateCartCount(count) {
    const cartCounter = document.querySelector('.cart-counter');
    if (cartCounter) {
        cartCounter.textContent = count;
        cartCounter.classList.toggle('d-none', count === 0);
    }
}

// Handle filter form submission
const filterForm = document.getElementById('filterForm');
if (filterForm) {
    filterForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const formData = new FormData(filterForm);
        const params = new URLSearchParams(formData);
        window.location.href = `${window.location.pathname}?${params.toString()}`;
    });
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', () => {
    initializeProductCards();
    
    // Initialize infinite scroll
    if (productGrid) {
        window.addEventListener('scroll', debounce(loadMoreProducts, 200));
    }
    
    // Initialize price range slider if it exists
    const priceRange = document.getElementById('price-range');
    if (priceRange && window.noUiSlider) {
        noUiSlider.create(priceRange, {
            start: [
                parseFloat(priceRange.dataset.minPrice) || 0,
                parseFloat(priceRange.dataset.maxPrice) || 1000000
            ],
            connect: true,
            range: {
                'min': parseFloat(priceRange.dataset.minPrice) || 0,
                'max': parseFloat(priceRange.dataset.maxPrice) || 1000000
            },
            format: {
                to: value => Math.round(value),
                from: value => Math.round(value)
            }
        });

        priceRange.noUiSlider.on('change', (values) => {
            document.getElementById('min_price').value = values[0];
            document.getElementById('max_price').value = values[1];
            filterForm.submit();
        });
    }
});