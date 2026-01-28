/**
 * Session Timeout Handler
 * 
 * Tracks user activity and automatically logs out after inactivity.
 * Shows a warning before logout to allow users to extend their session.
 * 
 * © 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 | https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
 */

(function() {
    'use strict';

    // Configuration (in milliseconds)
    const INACTIVITY_TIMEOUT = 30 * 60 * 1000;  // 30 minutes
    const WARNING_BEFORE = 2 * 60 * 1000;       // Show warning 2 minutes before logout
    const CHECK_INTERVAL = 30 * 1000;           // Check every 30 seconds

    // State
    let lastActivity = Date.now();
    let warningShown = false;
    let warningModal = null;

    // Events that reset the activity timer
    const ACTIVITY_EVENTS = [
        'mousedown', 'mousemove', 'keydown', 
        'scroll', 'touchstart', 'click'
    ];

    /**
     * Update last activity timestamp
     */
    function updateActivity() {
        lastActivity = Date.now();
        if (warningShown) {
            hideWarning();
        }
    }

    /**
     * Get time remaining before logout (in ms)
     */
    function getTimeRemaining() {
        return INACTIVITY_TIMEOUT - (Date.now() - lastActivity);
    }

    /**
     * Format time for display
     */
    function formatTime(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        
        if (minutes > 0) {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
        return `${remainingSeconds} seconds`;
    }

    /**
     * Get localized text based on page language
     */
    function getText(key) {
        const lang = document.documentElement.lang || 
                     document.querySelector('html').getAttribute('lang') || 
                     'en';
        
        const texts = {
            en: {
                title: 'Session Timeout Warning',
                message: 'Your session will expire due to inactivity.',
                timeLeft: 'Time remaining:',
                stayLoggedIn: 'Stay Logged In',
                logout: 'Log Out'
            },
            de: {
                title: 'Sitzungs-Timeout Warnung',
                message: 'Ihre Sitzung wird wegen Inaktivität ablaufen.',
                timeLeft: 'Verbleibende Zeit:',
                stayLoggedIn: 'Angemeldet bleiben',
                logout: 'Abmelden'
            },
            pl: {
                title: 'Ostrzeżenie o wygaśnięciu sesji',
                message: 'Twoja sesja wygaśnie z powodu braku aktywności.',
                timeLeft: 'Pozostały czas:',
                stayLoggedIn: 'Pozostań zalogowany',
                logout: 'Wyloguj'
            }
        };

        return (texts[lang] || texts['en'])[key];
    }

    /**
     * Create and show the warning modal
     */
    function showWarning() {
        if (warningShown) return;
        warningShown = true;

        // Create modal overlay
        warningModal = document.createElement('div');
        warningModal.id = 'session-timeout-modal';
        warningModal.innerHTML = `
            <div class="session-timeout-overlay">
                <div class="session-timeout-dialog">
                    <h3>${getText('title')}</h3>
                    <p>${getText('message')}</p>
                    <p class="session-timeout-timer">
                        ${getText('timeLeft')} <strong id="session-countdown"></strong>
                    </p>
                    <div class="session-timeout-actions">
                        <button id="session-stay" class="btn btn-primary">${getText('stayLoggedIn')}</button>
                        <button id="session-logout" class="btn btn-secondary">${getText('logout')}</button>
                    </div>
                </div>
            </div>
        `;

        // Add styles
        const styles = document.createElement('style');
        styles.textContent = `
            .session-timeout-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.6);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            }
            .session-timeout-dialog {
                background: white;
                padding: 2rem;
                border-radius: 8px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            }
            .session-timeout-dialog h3 {
                margin: 0 0 1rem 0;
                color: #2d3748;
            }
            .session-timeout-dialog p {
                margin: 0 0 1rem 0;
                color: #4a5568;
            }
            .session-timeout-timer {
                font-size: 1.25rem;
            }
            .session-timeout-timer strong {
                color: #c53030;
                font-size: 1.5rem;
            }
            .session-timeout-actions {
                display: flex;
                gap: 1rem;
                justify-content: center;
                margin-top: 1.5rem;
            }
            .session-timeout-actions .btn {
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 600;
            }
            .session-timeout-actions .btn-primary {
                background: #2f5233;
                color: white;
            }
            .session-timeout-actions .btn-primary:hover {
                background: #3d6b42;
            }
            .session-timeout-actions .btn-secondary {
                background: #e2e8f0;
                color: #4a5568;
            }
            .session-timeout-actions .btn-secondary:hover {
                background: #cbd5e0;
            }
        `;
        warningModal.appendChild(styles);

        document.body.appendChild(warningModal);

        // Add event listeners
        document.getElementById('session-stay').addEventListener('click', extendSession);
        document.getElementById('session-logout').addEventListener('click', doLogout);

        // Start countdown
        updateCountdown();
    }

    /**
     * Hide the warning modal
     */
    function hideWarning() {
        if (warningModal) {
            warningModal.remove();
            warningModal = null;
        }
        warningShown = false;
    }

    /**
     * Update the countdown timer in the warning
     */
    function updateCountdown() {
        if (!warningShown) return;

        const countdown = document.getElementById('session-countdown');
        if (!countdown) return;

        const remaining = getTimeRemaining();
        
        if (remaining <= 0) {
            doLogout();
            return;
        }

        countdown.textContent = formatTime(remaining);
        setTimeout(updateCountdown, 1000);
    }

    /**
     * Extend the session (user clicked "Stay Logged In")
     */
    function extendSession() {
        updateActivity();
        hideWarning();
        
        // Ping the server to refresh the session cookie
        fetch('/api/session/refresh', {
            method: 'POST',
            credentials: 'same-origin'
        }).catch(() => {
            // Silent fail - the activity update is what matters
        });
    }

    /**
     * Log out the user
     */
    function doLogout() {
        window.location.href = '/login?expired=1';
    }

    /**
     * Check session status periodically
     */
    function checkSession() {
        const remaining = getTimeRemaining();

        if (remaining <= 0) {
            doLogout();
            return;
        }

        if (remaining <= WARNING_BEFORE && !warningShown) {
            showWarning();
        }
    }

    /**
     * Initialize session timeout handling
     */
    function init() {
        // Only run on authenticated pages (check for session cookie or auth element)
        // Skip on login/register/public pages
        const publicPages = ['/login', '/register', '/forgot-password', '/reset-password'];
        const currentPath = window.location.pathname;
        
        if (publicPages.some(page => currentPath.startsWith(page))) {
            return;
        }

        // Check if user appears to be logged in (dashboard link visible, etc.)
        const dashboardLink = document.querySelector('a[href="/dashboard"]');
        const logoutLink = document.querySelector('a[href="/logout"]');
        
        if (!dashboardLink && !logoutLink) {
            // Probably not logged in, skip timeout handling
            return;
        }

        // Register activity listeners
        ACTIVITY_EVENTS.forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
        });

        // Start periodic checks
        setInterval(checkSession, CHECK_INTERVAL);
        
        // Initial check
        checkSession();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
