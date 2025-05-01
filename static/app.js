class WebSocketManager {
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
        this.connectWebSocket();
        this.setupEventListeners();
    }

    connectWebSocket() {
        this.updateConnectionStatus('connecting');
        
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = protocol + window.location.host + '/ws/row-count';
        console.log(`Connecting to ${wsUrl}`);
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = (e) => {
            console.log("WebSocket connected");
            this.reconnectAttempts = 0;
            this.updateConnectionStatus('connected');
            this.sendPing();
            this.startConnectionTimer();
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                
                if (data.type === 'count_update') {
                    this.updateCountDisplay(data.count);
                } else if (data.type === 'pong') {
                    console.log("Heartbeat acknowledged");
                    this.resetConnectionTimer();
                    // Schedule next ping after interval
                    setTimeout(() => this.sendPing(), this.pingIntervalTime);
                }
            } catch (e) {
                console.log("Received non-JSON message:", event.data);
            }
        };

        this.socket.onclose = (event) => {
            this.cleanupTimers();
            
            if (event.wasClean) {
                console.log(`Connection closed cleanly`);
                this.updateConnectionStatus('disconnected');
            } else {
                console.log('Connection died');
                this.handleDisconnection();
            }
        };

        this.socket.onerror = (error) => {
            console.log(`WebSocket error:`, error);
            this.updateConnectionStatus('error');
            this.socket.close();
        };
    }

    cleanupTimers() {
        clearTimeout(this.pingInterval);
        clearTimeout(this.connectionTimeout);
    }

    startConnectionTimer() {
        this.connectionTimeout = setTimeout(() => {
            console.log("Connection timeout - no response from server");
            this.updateConnectionStatus('reconnecting');
            this.socket.close();
        }, this.connectionTimeoutTime);
    }

    resetConnectionTimer() {
        clearTimeout(this.connectionTimeout);
        this.startConnectionTimer();
    }

    sendPing() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type: "ping" }));
        }
    }

    handleDisconnection() {
        if (this.autoReconnect) {
            this.updateConnectionStatus('reconnecting');
            this.attemptReconnect();
        } else {
            this.updateConnectionStatus('disconnected');
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            this.updateConnectionStatus('reconnecting');
            setTimeout(() => this.connectWebSocket(), this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.log('Max reconnection attempts reached');
            this.updateConnectionStatus('disconnected');
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
            if (!document.hidden && (!this.socket || this.socket.readyState === WebSocket.CLOSED)) {
                this.connectWebSocket();
            }
        });

        // Optional: Add manual reconnect button handler
        const reconnectBtn = document.getElementById('reconnect-btn');
        if (reconnectBtn) {
            reconnectBtn.addEventListener('click', () => {
                this.reconnectAttempts = 0;
                this.connectWebSocket();
            });
        }
    }
}

// Utility functions
function switchTab(event, tabId) {
    // Prevent default if event is provided
    if (event) event.preventDefault();
    
    // Remove 'active' class from all tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Add 'active' class to the clicked tab if event exists
    if (event) {
        event.currentTarget.classList.add('active');
    } else {
        // If no event, find the tab matching tabId and activate it
        const targetTab = document.querySelector(`.tab[data-tab="${tabId}"]`);
        if (targetTab) targetTab.classList.add('active');
    }

    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));

    // Show the target tab's content
    const targetContent = document.getElementById(tabId);
    if (targetContent) targetContent.classList.add('active');
}

function autoResize(textarea) {
    textarea.style.height = 'auto'; // Reset height
    textarea.style.height = textarea.scrollHeight + 'px'; // Set to scroll height
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize WebSocket connection
    const wsManager = new WebSocketManager();
    
    // Make it available globally if needed
    window.wsManager = wsManager;
    
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