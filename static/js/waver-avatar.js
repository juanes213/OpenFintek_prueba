// Waver Avatar - Professional E-commerce Agent Avatar
// Three states: Active, Inactive, Thinking

class WaverAvatar {
    constructor() {
        this.state = 'active'; // active, inactive, thinking
        this.initializeAvatars();
        this.setupEventListeners();
    }

    // SVG definitions for each state
    getAvatarSVG(state = 'active') {
        const avatars = {
            active: `
                <defs>
                    <linearGradient id="waveGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#7c3aed;stop-opacity:1">
                            <animate attributeName="stop-color" values="#7c3aed;#a78bfa;#7c3aed" dur="3s" repeatCount="indefinite" />
                        </stop>
                        <stop offset="100%" style="stop-color:#a78bfa;stop-opacity:1">
                            <animate attributeName="stop-color" values="#a78bfa;#7c3aed;#a78bfa" dur="3s" repeatCount="indefinite" />
                        </stop>
                    </linearGradient>
                    <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                        <feMerge>
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                
                <!-- Outer Ring -->
                <circle cx="50" cy="50" r="45" fill="none" stroke="url(#waveGradient)" stroke-width="2" opacity="0.3">
                    <animate attributeName="r" values="45;47;45" dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite" />
                </circle>
                
                <!-- Main Circle -->
                <circle cx="50" cy="50" r="40" fill="url(#waveGradient)" filter="url(#glow)">
                    <animate attributeName="r" values="40;42;40" dur="1.5s" repeatCount="indefinite" />
                </circle>
                
                <!-- Wave Pattern -->
                <path d="M 25 50 Q 37.5 35, 50 50 T 75 50" fill="none" stroke="#ffffff" stroke-width="2" opacity="0.8">
                    <animate attributeName="d" 
                        values="M 25 50 Q 37.5 35, 50 50 T 75 50;
                                M 25 50 Q 37.5 65, 50 50 T 75 50;
                                M 25 50 Q 37.5 35, 50 50 T 75 50" 
                        dur="2s" repeatCount="indefinite" />
                </path>
                
                <!-- Center Dot -->
                <circle cx="50" cy="50" r="5" fill="#ffffff">
                    <animate attributeName="r" values="5;7;5" dur="1.5s" repeatCount="indefinite" />
                </circle>
            `,
            
            inactive: `
                <defs>
                    <linearGradient id="inactiveGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#6b7280;stop-opacity:1" />
                        <stop offset="100%" style="stop-color:#4b5563;stop-opacity:1" />
                    </linearGradient>
                </defs>
                
                <!-- Outer Ring (static) -->
                <circle cx="50" cy="50" r="45" fill="none" stroke="#6b7280" stroke-width="1" opacity="0.2" />
                
                <!-- Main Circle -->
                <circle cx="50" cy="50" r="40" fill="url(#inactiveGradient)" opacity="0.7" />
                
                <!-- Wave Pattern (static) -->
                <path d="M 25 50 Q 37.5 50, 50 50 T 75 50" fill="none" stroke="#ffffff" stroke-width="2" opacity="0.3" />
                
                <!-- Center Dot -->
                <circle cx="50" cy="50" r="5" fill="#ffffff" opacity="0.5" />
            `,
            
            thinking: `
                <defs>
                    <linearGradient id="thinkingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#f59e0b;stop-opacity:1">
                            <animate attributeName="stop-color" values="#f59e0b;#fbbf24;#f59e0b" dur="1s" repeatCount="indefinite" />
                        </stop>
                        <stop offset="100%" style="stop-color:#fbbf24;stop-opacity:1">
                            <animate attributeName="stop-color" values="#fbbf24;#f59e0b;#fbbf24" dur="1s" repeatCount="indefinite" />
                        </stop>
                    </linearGradient>
                </defs>
                
                <!-- Spinning Outer Ring -->
                <g transform-origin="50 50">
                    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="3s" repeatCount="indefinite" />
                    <circle cx="50" cy="50" r="45" fill="none" stroke="url(#thinkingGradient)" stroke-width="2" opacity="0.4" stroke-dasharray="10 5" />
                </g>
                
                <!-- Main Circle -->
                <circle cx="50" cy="50" r="40" fill="url(#thinkingGradient)">
                    <animate attributeName="opacity" values="0.8;1;0.8" dur="1s" repeatCount="indefinite" />
                </circle>
                
                <!-- Thinking Dots -->
                <g>
                    <circle cx="35" cy="50" r="4" fill="#ffffff">
                        <animate attributeName="opacity" values="0;1;0" dur="1.5s" repeatCount="indefinite" begin="0s" />
                    </circle>
                    <circle cx="50" cy="50" r="4" fill="#ffffff">
                        <animate attributeName="opacity" values="0;1;0" dur="1.5s" repeatCount="indefinite" begin="0.5s" />
                    </circle>
                    <circle cx="65" cy="50" r="4" fill="#ffffff">
                        <animate attributeName="opacity" values="0;1;0" dur="1.5s" repeatCount="indefinite" begin="1s" />
                    </circle>
                </g>
            `
        };

        return avatars[state] || avatars.active;
    }

    // Initialize all avatar locations
    initializeAvatars() {
        // Logo avatar
        const logoAvatar = document.getElementById('waverLogo');
        if (logoAvatar) {
            logoAvatar.innerHTML = this.getAvatarSVG('active');
        }

        // Message avatars
        const messageAvatars = document.querySelectorAll('.avatar-svg:not(.thinking)');
        messageAvatars.forEach(avatar => {
            avatar.innerHTML = this.getAvatarSVG('active');
        });

        // Thinking avatar
        const thinkingAvatar = document.querySelector('.avatar-svg.thinking');
        if (thinkingAvatar) {
            thinkingAvatar.innerHTML = this.getAvatarSVG('thinking');
        }
    }

    // Update avatar state
    setState(newState) {
        this.state = newState;
        
        // Update logo
        const logoAvatar = document.getElementById('waverLogo');
        if (logoAvatar) {
            logoAvatar.innerHTML = this.getAvatarSVG(newState);
        }

        // Update status indicator
        const statusIndicator = document.querySelector('.status-indicator');
        const statusText = document.querySelector('.status-text');
        
        if (statusIndicator && statusText) {
            // Remove all state classes
            statusIndicator.classList.remove('active', 'inactive', 'thinking');
            
            // Add new state class and update text
            switch(newState) {
                case 'active':
                    statusIndicator.classList.add('active');
                    statusText.textContent = 'En línea';
                    break;
                case 'inactive':
                    statusIndicator.classList.add('inactive');
                    statusText.textContent = 'Inactivo';
                    break;
                case 'thinking':
                    statusIndicator.classList.add('thinking');
                    statusText.textContent = 'Procesando';
                    break;
            }
        }
    }

    // Add avatar to new message
    addMessageAvatar(messageElement, isBot = true) {
        const avatarContainer = messageElement.querySelector('.message-avatar');
        if (avatarContainer) {
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('class', 'avatar-svg');
            svg.setAttribute('width', '32');
            svg.setAttribute('height', '32');
            svg.setAttribute('viewBox', '0 0 100 100');
            
            if (isBot) {
                svg.innerHTML = this.getAvatarSVG('active');
            } else {
                // User avatar (simple circle with initial)
                svg.innerHTML = `
                    <circle cx="50" cy="50" r="45" fill="#7c3aed" />
                    <text x="50" y="50" text-anchor="middle" dy=".3em" fill="white" font-size="40" font-weight="600">U</text>
                `;
            }
            
            avatarContainer.appendChild(svg);
        }
    }

    // Setup event listeners
    setupEventListeners() {
        // Listen for custom events
        document.addEventListener('waverStateChange', (e) => {
            this.setState(e.detail.state);
        });

        // Auto-idle detection
        let idleTimer;
        const setIdle = () => {
            this.setState('inactive');
        };

        const resetIdle = () => {
            clearTimeout(idleTimer);
            if (this.state === 'inactive') {
                this.setState('active');
            }
            idleTimer = setTimeout(setIdle, 60000); // 1 minute idle time
        };

        // Reset idle on user activity
        ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, resetIdle, true);
        });

        // Initialize idle timer
        resetIdle();
    }

    // Animate avatar on hover
    setupHoverEffects() {
        const avatars = document.querySelectorAll('.avatar-svg');
        avatars.forEach(avatar => {
            avatar.addEventListener('mouseenter', () => {
                avatar.style.transform = 'scale(1.1)';
                avatar.style.transition = 'transform 0.3s ease';
            });
            
            avatar.addEventListener('mouseleave', () => {
                avatar.style.transform = 'scale(1)';
            });
        });
    }
}

// Initialize Waver Avatar when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.waverAvatar = new WaverAvatar();
    
    // Example: Change state when sending message
    const originalSendMessage = window.sendMessage;
    if (originalSendMessage) {
        window.sendMessage = function(...args) {
            // Set thinking state
            document.dispatchEvent(new CustomEvent('waverStateChange', { 
                detail: { state: 'thinking' } 
            }));
            
            // Call original function
            const result = originalSendMessage.apply(this, args);
            
            // Set active state after response
            if (result && result.then) {
                result.then(() => {
                    document.dispatchEvent(new CustomEvent('waverStateChange', { 
                        detail: { state: 'active' } 
                    }));
                });
            }
            
            return result;
        };
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WaverAvatar;
}
