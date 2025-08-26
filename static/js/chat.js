// Waver Chat Application - Professional E-commerce Assistant
// Enhanced with animations and modern UI interactions

class WaverChat {
    constructor() {
        // DOM Elements
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.chatForm = document.getElementById('chatForm');
        this.clearChatBtn = document.getElementById('clearChatBtn');
        this.toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
        this.historyModal = document.getElementById('historyModal');
        this.closeModal = document.getElementById('closeModal');
        this.historyContent = document.getElementById('historyContent');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.charCounter = document.getElementById('charCounter');
        this.scrollToBottomBtn = document.getElementById('scrollToBottomBtn');
        
        // Sidebar elements
        this.sidebar = document.querySelector('.sidebar');
        this.sidebarOverlay = document.getElementById('sidebarOverlay');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.sidebarClose = document.getElementById('sidebarClose');
        this.chatContainer = document.querySelector('.chat-container');
        
        // Token Metrics Elements
        this.tokenMetrics = document.getElementById('tokenMetrics');
        this.tokensPerSecEl = document.getElementById('tokensPerSec');
        this.totalTokensEl = document.getElementById('totalTokens');
        this.executionTimeEl = document.getElementById('executionTime');
        
        // Connection Status Elements
        this.connectionStatus = document.getElementById('connectionStatus');
        this.connectionText = document.getElementById('connectionText');
        
        
        // State
        this.isLoading = false;
        this.conversationHistory = [];
        this.typingTimeout = null;
        this.isAtBottom = true;
        
        // Token Metrics State
        this.totalTokensUsed = 0;
        this.requestStartTime = null;
        this.metricsUpdateInterval = null;
        
        this.init();
    }
    
    init() {
        // Event listeners
        this.setupEventListeners();
        
        // Initialize UI
        this.initializeUI();
        
        // Load saved data
        this.loadLocalHistory();
        
        // Initialize animations
        this.initializeAnimations();
    }
    
    setupEventListeners() {
        // Form submission
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Buttons
        this.clearChatBtn?.addEventListener('click', () => this.clearChat());
        this.closeModal?.addEventListener('click', () => this.hideHistory());
        this.scrollToBottomBtn?.addEventListener('click', () => this.scrollToBottom(true));
        
        // Sidebar toggle
        this.sidebarToggle?.addEventListener('click', () => this.toggleSidebar());
        this.sidebarClose?.addEventListener('click', () => this.closeSidebar());
        this.toggleSidebarBtn?.addEventListener('click', () => this.toggleSidebar());
        
        // Mobile overlay
        this.sidebarOverlay?.addEventListener('click', () => this.closeSidebar());
        
        
        // Navigation items
        document.querySelectorAll('.nav-item[data-section]').forEach(item => {
            item.addEventListener('click', (e) => this.handleNavigation(e));
        });
        
        // Modal
        this.historyModal?.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                this.hideHistory();
            }
        });
        
        // Input events
        this.messageInput?.addEventListener('input', () => this.updateCharCounter());
        this.messageInput?.addEventListener('keydown', (e) => this.handleInputKeydown(e));
        
        // Enhanced keyboard shortcuts and focus management
        document.addEventListener('keydown', (e) => this.handleGlobalKeyDown(e));
    }
    
    initializeUI() {
        // Set initial timestamp
        this.updateInitialTime();
        
        // Focus input
        this.messageInput?.focus();
        
        // Initialize character counter
        this.updateCharCounter();
        
        // Load sidebar state (si es minimal, forzar abierto)
        const app = document.querySelector('.app-container');
        if (app?.classList.contains('minimal')) {
            this.openSidebar();
        } else {
            this.loadSidebarState();
        }
        
    }
    
    initializeAnimations() {
        // Add smooth scroll behavior
        this.chatMessages?.addEventListener('scroll', () => {
            this.handleScroll();
        });
        
        // Animate initial message
        const initialMessage = document.querySelector('.message-group');
        if (initialMessage) {
            initialMessage.style.animation = 'messageSlide 0.5s ease-out';
        }
    }
    
    updateInitialTime() {
        const initialTimeElement = document.getElementById('initialTime');
        if (initialTimeElement) {
            initialTimeElement.textContent = this.formatTime(new Date());
        }
    }
    
    async handleSubmit(e) {
        e.preventDefault();
        
        const message = this.messageInput.value.trim();
        if (!message || this.isLoading) return;
        
        // Agregar mensaje del usuario
        this.addUserMessage(message);
        
        // Limpiar input
        this.messageInput.value = '';
        
        // Mostrar estado de carga
        this.setLoading(true);
        this.startTokenMetrics();
        
        try {
            // Enviar mensaje al backend
            const response = await this.sendMessage(message);
            
            // Agregar respuesta del bot
            this.addBotMessage(response.respuesta, response.intencion);
            
            // Actualizar métricas con datos del servidor (si están disponibles)
            this.updateTokenMetrics(response);
            
            // Guardar en historial local
            this.saveToLocalHistory({
                userMessage: message,
                botResponse: response.respuesta,
                intent: response.intencion,
                timestamp: new Date(),
                tokens: response.tokens || null
            });
            
        } catch (error) {
            console.error('Error:', error);
            this.showConnectionStatus('disconnected', 'Error de conexión');
            this.addBotMessage(
                'Lo siento, ocurrió un error al procesar tu mensaje. Por favor intenta nuevamente.',
                'error'
            );
        } finally {
            this.setLoading(false);
            this.stopTokenMetrics();
            this.messageInput.focus();
        }
    }
    
    async sendMessage(message) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mensaje: message })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    addUserMessage(message) {
        const messageElement = this.createMessageElement(message, 'user');
        messageElement.classList.add('sending');
        this.chatMessages.appendChild(messageElement);
        this.scrollToBottom();
        
        // Simular estados de mensaje
        setTimeout(() => {
            messageElement.classList.remove('sending');
            this.updateMessageStatus(messageElement, 'sent');
        }, 500);
        
        setTimeout(() => {
            this.updateMessageStatus(messageElement, 'delivered');
        }, 1000);
        
        return messageElement;
    }
    
    addBotMessage(message, intent = null) {
        const messageElement = this.createMessageElement(message, 'bot', intent);
        this.chatMessages.appendChild(messageElement);
        // Always scroll to bottom for new bot messages
        this.scrollToBottom(true);
    }
    
    createMessageElement(content, sender, intent = null) {
        if (!content || !sender) {
            console.error('createMessageElement: contenido o sender faltante');
            return document.createElement('div');
        }
        
        // Crear el grupo de mensaje con avatar
        const messageGroupDiv = document.createElement('div');
        messageGroupDiv.className = `message-group ${sender}-group`;
        messageGroupDiv.setAttribute('role', 'article');
        messageGroupDiv.setAttribute('aria-label', 
            sender === 'user' ? 'Tu mensaje' : 'Mensaje de Waver'
        );
        
        // Avatar para el agente (solo para bot)
        if (sender === 'bot') {
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'message-avatar';
            const avatarSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            avatarSvg.setAttribute('class', 'avatar-svg');
            avatarSvg.setAttribute('width', '32');
            avatarSvg.setAttribute('height', '32');
            avatarSvg.setAttribute('viewBox', '0 0 100 100');
            // Insertar el SVG animado azul del avatar
            try {
                if (window.waverAvatar && typeof window.waverAvatar.getAvatarSVG === 'function') {
                    avatarSvg.innerHTML = window.waverAvatar.getAvatarSVG('active');
                }
            } catch (e) {
                // Silencioso: si falla, se llenará por inicializador global
            }
            avatarDiv.appendChild(avatarSvg);
            messageGroupDiv.appendChild(avatarDiv);
        }
        
        // Wrapper de contenido
        const contentWrapperDiv = document.createElement('div');
        contentWrapperDiv.className = 'message-content-wrapper';
        
    // Encabezado con autor (y avatar inline para bot)
        const headerDiv = document.createElement('div');
        headerDiv.className = 'message-header';
        const authorDiv = document.createElement('div');
        authorDiv.className = 'message-author';
        authorDiv.appendChild(document.createTextNode(sender === 'user' ? 'Tú' : 'Waver'));
        headerDiv.appendChild(authorDiv);
        
        // Mensaje
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const messageTextDiv = document.createElement('div');
        messageTextDiv.className = 'message-text';
        messageTextDiv.innerHTML = this.escapeHtml(content);
        messageDiv.appendChild(messageTextDiv);
        
        // Para bot: hora debajo del chat (no debajo del autor)
        if (sender !== 'user') {
            // Encabezado
            contentWrapperDiv.appendChild(headerDiv);
            // Mensaje primero
            contentWrapperDiv.appendChild(messageDiv);
            // Hora debajo del mensaje
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            const timeText = document.createElement('span');
            timeText.textContent = this.formatTime(new Date());
            timeDiv.appendChild(timeText);
            contentWrapperDiv.appendChild(timeDiv);
        } else {
            // Para user: burbuja + hora debajo (centrada) y avatar a la derecha
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            const timeText = document.createElement('span');
            timeText.textContent = this.formatTime(new Date());
            timeDiv.appendChild(timeText);

            // Columna derecha (contenido): 'Tú' arriba, burbuja, hora
            const contentCol = document.createElement('div');
            contentCol.className = 'user-bubble-col';
            contentCol.appendChild(headerDiv); // 'Tú' arriba
            contentCol.appendChild(messageDiv); // burbuja
            contentCol.appendChild(timeDiv); // hora debajo

            // Avatar a la derecha de la burbuja
            const avatar = document.createElement('div');
            avatar.className = 'user-bubble-avatar';
            avatar.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                </svg>
            `;

            const row = document.createElement('div');
            row.className = 'user-bubble-row';
            // Estructura: contenido a la derecha, avatar aún más a la derecha
            row.appendChild(contentCol);
            row.appendChild(avatar);

            contentWrapperDiv.appendChild(row);
        }
        messageGroupDiv.appendChild(contentWrapperDiv);
        
    return messageGroupDiv;
    }
    
    updateMessageStatus(messageElement, status) {
        // Buscar el icono de estado dentro del grupo del mensaje
        const group = messageElement.closest ? (messageElement.closest('.message-group') || messageElement) : messageElement;
        const statusIcon = group.querySelector('.status-icon');
        if (!statusIcon) return;
        
        statusIcon.classList.remove('sent', 'delivered', 'read');
        statusIcon.classList.add(status);
        
        // Update icon based on status
        const svgPaths = {
            sent: 'M9 11l3 3L22 4',
            delivered: 'M9 11l3 3L22 4M9 11l3 3L22 4',
            read: 'M9 11l3 3L22 4M9 11l3 3L22 4'
        };
        
        if (status === 'delivered') {
            statusIcon.innerHTML = `
                <path d="M9 11l3 3L22 4"/>
                <path d="M4 11l3 3L11 8" opacity="0.5"/>
            `;
        } else if (status === 'read') {
            statusIcon.innerHTML = `
                <path d="M9 11l3 3L22 4"/>
                <path d="M4 11l3 3L11 8"/>
            `;
        }
    }
    
    formatIntent(intent) {
        const intentMap = {
            'consulta_pedido': 'Consulta de Pedido',
            'consulta_producto': 'Consulta de Producto',
            'politicas_empresa': 'Políticas',
            'informacion_general': 'Información General',
            'escalacion_humana': 'Escalación Humana',
            'error': 'Error'
        };
        return intentMap[intent] || intent;
    }
    
    formatTime(date) {
        return date.toLocaleTimeString('es-ES', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    formatMarkdown(text) {
        // Convertir texto con formato Markdown a HTML
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // **texto** -> <strong>texto</strong>
            .replace(/\*(.*?)\*/g, '<em>$1</em>') // *texto* -> <em>texto</em>
            .replace(/\n/g, '<br>'); // Saltos de línea
    }
    
    escapeHtml(text) {
        // Primero procesar markdown, luego escapar el resto
        const markdownProcessed = this.formatMarkdown(text);
        return markdownProcessed; // Ya no necesitamos escapar porque procesamos markdown
    }
    
    scrollToBottom(forced = false, smooth = true) {
        if (!this.chatMessages) return;
        
        const shouldScroll = forced || this.isAtBottom;
        const behavior = (forced && smooth) ? 'smooth' : 'auto';
        
        if (shouldScroll) {
            // Use requestAnimationFrame for better performance
            requestAnimationFrame(() => {
                this.chatMessages.scrollTo({
                    top: this.chatMessages.scrollHeight,
                    behavior: behavior
                });
                this.isAtBottom = true;
                
                // Update scroll button visibility
                this.updateScrollButton();
            });
        }
    }
    
    updateScrollButton() {
        if (!this.scrollToBottomBtn || !this.chatMessages) return;
        
        const { scrollTop, scrollHeight, clientHeight } = this.chatMessages;
        const isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;
        
        if (isNearBottom) {
            this.scrollToBottomBtn.classList.remove('visible');
        } else {
            this.scrollToBottomBtn.classList.add('visible');
        }
    }
    
    smoothScrollToElement(element) {
        if (!element || !this.chatMessages) return;
        
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'nearest'
        });
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        if (this.sendButton) this.sendButton.disabled = loading;
        
        const sendIcon = this.sendButton?.querySelector('.send-icon');
        const loadingIcon = this.sendButton?.querySelector('.loading-icon');
        
        if (loading) {
            this.sendButton?.classList.add('sending');
            this.showTypingIndicator();
            sendIcon?.style.setProperty('display', 'none');
            loadingIcon?.style.setProperty('display', 'block');
            
            // Change avatar state to thinking
            document.dispatchEvent(new CustomEvent('waverStateChange', { 
                detail: { state: 'thinking' } 
            }));
        } else {
            this.sendButton?.classList.remove('sending');
            this.hideTypingIndicator();
            sendIcon?.style.setProperty('display', 'block');
            loadingIcon?.style.setProperty('display', 'none');
            
            // Change avatar state back to active
            document.dispatchEvent(new CustomEvent('waverStateChange', { 
                detail: { state: 'active' } 
            }));
        }
        
        this.updateCharCounter();
    }
    
    showConnectionStatus(status, message) {
        if (!this.connectionStatus || !this.connectionText) return;
        
        this.connectionStatus.className = `connection-status visible ${status}`;
        this.connectionText.textContent = message;
        
        // Auto-hide after 3 seconds for connected status
        if (status === 'connected') {
            setTimeout(() => {
                this.hideConnectionStatus();
            }, 3000);
        }
    }
    
    hideConnectionStatus() {
        this.connectionStatus?.classList.remove('visible');
    }
    
    showTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'flex';
            this.typingIndicator.style.animation = 'fadeIn 0.3s ease-out';
        }
    }
    
    hideTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => {
                this.typingIndicator.style.display = 'none';
            }, 300);
        }
    }
    
    updateCharCounter() {
        if (this.charCounter && this.messageInput) {
            const length = this.messageInput.value.length;
            const maxLength = this.messageInput.maxLength;
            this.charCounter.textContent = `${length}/${maxLength}`;
            
            // Change color when near limit
            if (length > maxLength * 0.9) {
                this.charCounter.style.color = 'var(--status-error)';
            } else if (length > maxLength * 0.7) {
                this.charCounter.style.color = 'var(--status-thinking)';
            } else {
                this.charCounter.style.color = 'var(--text-muted)';
            }
        }
    }
    
    handleNavigation(e) {
        const section = e.currentTarget.dataset.section;
        
        // Update active state
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        e.currentTarget.classList.add('active');
        
        // Handle section display
        switch(section) {
            case 'history':
                this.showHistory();
                break;
            case 'settings':
                // Future implementation
                console.log('Settings section');
                break;
            case 'chat':
            default:
                // Return to chat
                break;
        }
    }
    
    handleInputKeydown(e) {
        // Submit on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.chatForm.dispatchEvent(new Event('submit'));
        }
        
        // Clear on Ctrl+K
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            this.messageInput.value = '';
            this.updateCharCounter();
        }
    }
    
    handleGlobalKeyDown(e) {
        // Escape key handling
        if (e.key === 'Escape') {
            if (this.historyModal?.style.display === 'flex') {
                this.hideHistory();
                this.restoreFocus();
                return;
            }
            if (!this.sidebar?.classList.contains('closed')) {
                this.closeSidebar();
                this.messageInput?.focus();
                return;
            }
        }
        
        // Focus shortcuts
        if (e.ctrlKey && e.key === '/') {
            e.preventDefault();
            this.focusMessageInput();
        }
        
        // Navigation shortcuts
        if (e.ctrlKey && e.shiftKey && e.key === 'H') {
            e.preventDefault();
            this.showHistory();
        }
        
        if (e.ctrlKey && e.shiftKey && e.key === 'S') {
            e.preventDefault();
            this.toggleSidebar();
        }
        
        // Clear chat shortcut
        if (e.ctrlKey && e.shiftKey && e.key === 'N') {
            e.preventDefault();
            this.clearChat();
        }
        
    }
    
    focusMessageInput() {
        if (this.messageInput) {
            this.messageInput.focus();
            this.messageInput.setSelectionRange(this.messageInput.value.length, this.messageInput.value.length);
        }
    }
    
    storeFocus() {
        this.lastFocusedElement = document.activeElement;
    }
    
    restoreFocus() {
        if (this.lastFocusedElement && this.lastFocusedElement !== document.body) {
            this.lastFocusedElement.focus();
        } else {
            this.focusMessageInput();
        }
    }
    
    handleScroll() {
        if (!this.chatMessages) return;
        
        const { scrollTop, scrollHeight, clientHeight } = this.chatMessages;
        const isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;
        
        this.isAtBottom = isNearBottom;
        this.updateScrollButton();
        
        // Throttle scroll events for better performance
        if (this.scrollTimeout) clearTimeout(this.scrollTimeout);
        this.scrollTimeout = setTimeout(() => {
            this.onScrollEnd();
        }, 150);
    }
    
    onScrollEnd() {
        // Mark messages as read when they come into view
        if (this.isAtBottom) {
            this.markVisibleMessagesAsRead();
        }
    }
    
    markVisibleMessagesAsRead() {
        const userGroups = this.chatMessages.querySelectorAll('.message-group.user-group');
        userGroups.forEach(group => {
            const statusIcon = group.querySelector('.status-icon');
            if (statusIcon && !statusIcon.classList.contains('read')) {
                this.updateMessageStatus(group, 'read');
            }
        });
    }
    
    // Sidebar methods
    toggleSidebar() {
        if (this.sidebar?.classList.contains('closed')) {
            this.openSidebar();
        } else {
            this.closeSidebar();
        }
    }

    openSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.remove('closed');
        }
        localStorage.setItem('sidebarOpen', 'true');
    }

    closeSidebar() {
        if (this.sidebar) {
            this.sidebar.classList.add('closed');
        }
        localStorage.setItem('sidebarOpen', 'false');
    }

    loadSidebarState() {
        // Por defecto el sidebar está abierto
        const isOpen = localStorage.getItem('sidebarOpen') !== 'false';
        if (isOpen) {
            this.openSidebar();
        } else {
            this.closeSidebar();
        }
    }

    
    clearChat() {
        // Mantener solo el mensaje de bienvenida inicial
        const initialMessage = this.chatMessages.querySelector('.bot-message');
        this.chatMessages.innerHTML = '';
        if (initialMessage) {
            this.chatMessages.appendChild(initialMessage.cloneNode(true));
            this.updateInitialTime();
        }
        
        // Limpiar historial local
        this.clearLocalHistory();
        
        // Resetear métricas de tokens
        this.resetTokenMetrics();
        
        // En modo minimal, mantener el sidebar visible
        const app = document.querySelector('.app-container');
        if (app?.classList.contains('minimal')) {
            this.openSidebar();
        } else {
            // Close sidebar on clear (optional)
            this.closeSidebar();
        }
        
        this.messageInput.focus();
    }
    
    async showHistory() {
        this.storeFocus();
        this.historyContent.innerHTML = '<div style="text-align: center; padding: 20px;">Cargando historial...</div>';
        this.historyModal.style.display = 'flex';
        
        // Focus the close button for keyboard accessibility
        setTimeout(() => {
            this.closeModal?.focus();
        }, 100);
        
        try {
            // Cargar historial del servidor
            const response = await fetch('/api/chat/history');
            const data = await response.json();
            
            if (data.history && data.history.length > 0) {
                this.displayHistory(data.history);
            } else {
                this.historyContent.innerHTML = '<div style="text-align: center; padding: 20px; color: #6c757d;">No hay conversaciones en el historial.</div>';
            }
        } catch (error) {
            console.error('Error loading history:', error);
            // Mostrar historial local como fallback
            if (this.conversationHistory.length > 0) {
                this.displayLocalHistory();
            } else {
                this.historyContent.innerHTML = '<div style="text-align: center; padding: 20px; color: #dc3545;">Error cargando el historial.</div>';
            }
        }
    }
    
    displayHistory(history) {
        let historyHtml = '';
        
        history.forEach(item => {
            const timestamp = new Date(item.timestamp).toLocaleString('es-ES');
            const intent = this.formatIntent(item.intencion);
            
            historyHtml += `
                <div class="history-item">
                    <div class="history-timestamp">${timestamp}</div>
                    <div class="history-message history-user">Usuario: ${this.escapeHtml(item.mensaje_usuario)}</div>
                    <div class="history-message history-bot">Waver: ${this.escapeHtml(item.respuesta_bot)}</div>
                    <div class="history-intent">Categoría: ${intent}</div>
                </div>
            `;
        });
        
        this.historyContent.innerHTML = historyHtml;
    }
    
    displayLocalHistory() {
        let historyHtml = '<div class="history-notice">Historial local (sesión actual)</div>';
        
        this.conversationHistory.slice(-10).forEach(item => {
            const timestamp = item.timestamp.toLocaleString('es-ES');
            const intent = this.formatIntent(item.intent);
            
            historyHtml += `
                <div class="history-item">
                    <div class="history-timestamp">${timestamp}</div>
                    <div class="history-message history-user">Usuario: ${this.escapeHtml(item.userMessage)}</div>
                    <div class="history-message history-bot">Waver: ${this.escapeHtml(item.botResponse)}</div>
                    <div class="history-intent">Categoría: ${intent}</div>
                </div>
            `;
        });
        
        this.historyContent.innerHTML = historyHtml;
    }
    
    hideHistory() {
        this.historyModal.style.display = 'none';
        this.restoreFocus();
    }
    
    saveToLocalHistory(item) {
        this.conversationHistory.push(item);
        
        // Mantener solo los últimos 50 elementos
        if (this.conversationHistory.length > 50) {
            this.conversationHistory = this.conversationHistory.slice(-50);
        }
        
        // Guardar en localStorage
        localStorage.setItem('chatbot_history', JSON.stringify(this.conversationHistory));
    }
    
    loadLocalHistory() {
        try {
            const saved = localStorage.getItem('chatbot_history');
            if (saved) {
                this.conversationHistory = JSON.parse(saved).map(item => ({
                    ...item,
                    timestamp: new Date(item.timestamp)
                }));
            }
        } catch (error) {
            console.error('Error loading local history:', error);
            this.conversationHistory = [];
        }
    }
    
    clearLocalHistory() {
        this.conversationHistory = [];
        localStorage.removeItem('chatbot_history');
    }
    
    
    // Token Metrics Methods
    startTokenMetrics() {
        this.requestStartTime = Date.now();
        
        // Mostrar panel de métricas
        if (this.tokenMetrics) {
            this.tokenMetrics.classList.remove('hidden');
        }
        
        // Iniciar actualización del tiempo de ejecución
        this.metricsUpdateInterval = setInterval(() => {
            this.updateExecutionTime();
        }, 100);
    }
    
    stopTokenMetrics() {
        if (this.metricsUpdateInterval) {
            clearInterval(this.metricsUpdateInterval);
            this.metricsUpdateInterval = null;
        }
        this.updateExecutionTime();
    }
    
    updateExecutionTime() {
        if (this.requestStartTime && this.executionTimeEl) {
            const elapsed = (Date.now() - this.requestStartTime) / 1000;
            this.executionTimeEl.textContent = `${elapsed.toFixed(1)}s`;
        }
    }
    
    updateTokenMetrics(response) {
        // Esta función será llamada con los datos reales del servidor
        // Por ahora, usamos valores simulados para demostración
        const tokens = response.tokens || {
            prompt_tokens: Math.floor(Math.random() * 100) + 50,
            completion_tokens: Math.floor(Math.random() * 200) + 100,
            total_tokens: 0
        };
        tokens.total_tokens = tokens.prompt_tokens + tokens.completion_tokens;
        
        // Calcular tokens por segundo
        const executionTime = (Date.now() - this.requestStartTime) / 1000;
        const tokensPerSec = executionTime > 0 ? (tokens.completion_tokens / executionTime).toFixed(1) : 0;
        
        // Actualizar total acumulado
        this.totalTokensUsed += tokens.total_tokens;
        
        // Actualizar elementos del DOM con animación
        this.animateMetricUpdate(this.tokensPerSecEl, tokensPerSec);
        this.animateMetricUpdate(this.totalTokensEl, this.totalTokensUsed);
    }
    
    animateMetricUpdate(element, value) {
        if (!element) return;
        
        element.classList.add('updating');
        element.textContent = value.toString();
        
        setTimeout(() => {
            element.classList.remove('updating');
        }, 300);
    }
    
    resetTokenMetrics() {
        this.totalTokensUsed = 0;
        if (this.tokensPerSecEl) this.tokensPerSecEl.textContent = '0';
        if (this.totalTokensEl) this.totalTokensEl.textContent = '0';
        if (this.executionTimeEl) this.executionTimeEl.textContent = '0.0s';
        if (this.tokenMetrics) this.tokenMetrics.classList.add('hidden');
    }
}

// Initialize Waver Chat Application
document.addEventListener('DOMContentLoaded', () => {
    window.waverChat = new WaverChat();
});

// Funciones de utilidad globales
window.ChatbotUtils = {
    // Función para probar la conectividad del API
    async testAPI() {
        try {
            const response = await fetch('/api/chat/health');
            const data = await response.json();
            console.log('API Health Check:', data);
            return data;
        } catch (error) {
            console.error('API Test failed:', error);
            return null;
        }
    },
    
    // Función para exportar historial
    exportHistory() {
        const saved = localStorage.getItem('chatbot_history');
        if (saved) {
            const blob = new Blob([saved], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `chatbot_history_${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } else {
            alert('No hay historial para exportar.');
        }
    }
};

// Service Worker para caché (opcional, para PWA)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Solo registrar si hay un service worker disponible
        // navigator.serviceWorker.register('/sw.js');
    });
}