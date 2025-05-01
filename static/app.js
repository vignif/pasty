class SocketIOManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.pingInterval = null;
        this.connectionTimeout = null;
        this.pingIntervalTime = 25000; // 25 seconds
        this.connectionTimeoutTime = 30000; // 30 seconds
        this.autoReconnect = true;
        
        this.init();
    }

    init() {
        this.connectSocket();
        this.setupEventListeners();
    }

    connectSocket() {
        this.updateConnectionStatus('connecting');
        
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const socketUrl = protocol + window.location.host;
        console.log(`Connecting to Socket.IO at ${socketUrl}`);
        
        this.socket = io(socketUrl, {
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay,
            reconnection: this.autoReconnect,
            transports: ['websocket']
        });

        this.socket.on('connect', () => {
            console.log("Socket.IO connected");
            this.reconnectAttempts = 0;
            this.updateConnectionStatus('connected');
            this.sendPing();
            this.startConnectionTimer();
        });

        this.socket.on('count_update', (data) => {
            this.updateCountDisplay(data.count);
        });

        this.socket.on('pong', (data) => {
            console.log("Heartbeat acknowledged", data);
            this.resetConnectionTimer();
            // Schedule next ping after interval
            setTimeout(() => this.sendPing(), this.pingIntervalTime);
        });

        this.socket.on('disconnect', (reason) => {
            this.cleanupTimers();
            
            if (reason === 'io server disconnect') {
                console.log('Disconnected by server');
                this.updateConnectionStatus('disconnected');
                // The server forcefully disconnected the socket, you might want to manually reconnect
                setTimeout(() => this.socket.connect(), 1000);
            } else {
                console.log('Connection lost:', reason);
                this.updateConnectionStatus('reconnecting');
            }
        });

        this.socket.on('connect_error', (error) => {
            console.log('Socket.IO connection error:', error);
            this.updateConnectionStatus('error');
        });

        this.socket.on('reconnect_attempt', (attempt) => {
            console.log(`Reconnection attempt ${attempt}`);
            this.reconnectAttempts = attempt;
            this.updateConnectionStatus('reconnecting');
        });

        this.socket.on('reconnect_failed', () => {
            console.log('Reconnection failed');
            this.updateConnectionStatus('disconnected');
        });
    }

    cleanupTimers() {
        clearTimeout(this.pingInterval);
        clearTimeout(this.connectionTimeout);
    }

    startConnectionTimer() {
        this.connectionTimeout = setTimeout(() => {
            console.log("Connection timeout - no response from server");
            this.updateConnectionStatus('reconnecting');
            this.socket.disconnect(); // This will trigger reconnection if enabled
        }, this.connectionTimeoutTime);
    }

    resetConnectionTimer() {
        clearTimeout(this.connectionTimeout);
        this.startConnectionTimer();
    }

    sendPing() {
        if (this.socket && this.socket.connected) {
            this.socket.emit('ping');
        }
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connection-status');
        if (!statusElement) return;
        
        // Remove all status classes
        statusElement.classList.remove(
            'connecting', 'connected', 'disconnected', 'reconnecting', 'error'
        );
        
        // Add current status class
        statusElement.classList.add(status);
        
        // Update status text
        const statusText = statusElement.querySelector('.status-text');
        if (statusText) {
            const statusMessages = {
                connecting: "Connecting...",
                connected: "Connected",
                disconnected: "Disconnected",
                reconnecting: `Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
                error: "Connection error"
            };
            statusText.textContent = statusMessages[status] || status;
        }
    }

    updateCountDisplay(count) {
        const countElement = document.getElementById('row-count');
        if (countElement) {
            countElement.textContent = count;
            countElement.classList.add('updated');
            setTimeout(() => countElement.classList.remove('updated'), 500);
        }
    }

    setupEventListeners() {
        // Reconnect when page becomes visible again
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && (!this.socket || !this.socket.connected)) {
                this.connectSocket();
            }
        });

        // Optional: Add manual reconnect button handler
        const reconnectBtn = document.getElementById('reconnect-btn');
        if (reconnectBtn) {
            reconnectBtn.addEventListener('click', () => {
                this.reconnectAttempts = 0;
                if (this.socket) {
                    this.socket.disconnect(); // Will trigger reconnection
                    this.socket.connect();
                } else {
                    this.connectSocket();
                }
            });
        }
    }
}

// Utility functions
function switchTab(event, tabId) {
    if (event) event.preventDefault();
    
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));

    if (event) {
        event.currentTarget.classList.add('active');
    } else {
        const targetTab = document.querySelector(`.tab[data-tab="${tabId}"]`);
        if (targetTab) targetTab.classList.add('active');
    }

    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));

    const targetContent = document.getElementById(tabId);
    if (targetContent) targetContent.classList.add('active');
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Initialize when DOM is loaded
// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Socket.IO manager
    const socketManager = new SocketIOManager();
    window.socketManager = socketManager;
    
    // Initialize tabs if they exist
    const defaultTab = document.querySelector('.tab.active');
    if (defaultTab) {
        const tabId = defaultTab.dataset.tab || defaultTab.getAttribute('onclick').match(/'(.*?)'/)[1];
        switchTab(null, tabId);
    }
    
    // Setup auto-resize for textareas
    const textareas = document.querySelectorAll('textarea[data-autoresize]');
    textareas.forEach(textarea => {
        autoResize(textarea);
        textarea.addEventListener('input', () => autoResize(textarea));
    });
});