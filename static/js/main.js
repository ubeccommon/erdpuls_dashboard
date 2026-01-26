/**
 * Erdpuls Collective Threshold Model - Main JavaScript
 */

// Flash message auto-dismiss
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-10px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
});

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('de-DE', {
        style: 'currency',
        currency: 'EUR'
    }).format(amount);
}

// Token to EUR conversion
function tokensToEur(tokens, rate) {
    return tokens / rate;
}

// Hours to EUR conversion
function hoursToEur(hours, ratePerHour) {
    return hours * ratePerHour;
}

// Real-time calculation for contribution forms
document.addEventListener('DOMContentLoaded', function() {
    const tokenInput = document.getElementById('tokens');
    const hoursInput = document.getElementById('hours');
    const categorySelect = document.getElementById('hours_category');
    
    if (tokenInput) {
        tokenInput.addEventListener('input', function() {
            const tokens = parseFloat(this.value) || 0;
            const rate = parseFloat(document.querySelector('.token-rate-info')?.dataset?.rate || 70);
            const eur = tokensToEur(tokens, rate);
            // Could show calculated EUR value here
        });
    }
    
    if (hoursInput && categorySelect) {
        const updateHoursValue = () => {
            const hours = parseFloat(hoursInput.value) || 0;
            const option = categorySelect.selectedOptions[0];
            const rate = parseFloat(option?.dataset?.rate || 10);
            const eur = hoursToEur(hours, rate);
            // Could show calculated EUR value here
        };
        
        hoursInput.addEventListener('input', updateHoursValue);
        categorySelect.addEventListener('change', updateHoursValue);
    }
});

// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// API helper functions
const API = {
    async getOfferingProgress(offeringId) {
        const response = await fetch(`/api/offerings/${offeringId}/progress`);
        return response.json();
    },
    
    async getFundBalance() {
        const response = await fetch('/api/fund/balance');
        return response.json();
    },
    
    async getTokenRate() {
        const response = await fetch('/api/rates/tokens');
        return response.json();
    },
    
    async getHoursRates() {
        const response = await fetch('/api/rates/hours');
        return response.json();
    }
};

// Export for use in other scripts
window.ErdpulsThreshold = {
    API,
    formatCurrency,
    tokensToEur,
    hoursToEur
};
