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
        this.setupFormHandlers();
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
            setTimeout(() => this.sendPing(), this.pingIntervalTime);
        });

        this.socket.on('save_success', (data) => {
            this.showSaveSuccess(data.id, data.content);
        });

        this.socket.on('save_error', (data) => {
            this.showError(data.error);
        });

        this.socket.on('retrieve_success', (data) => {
            this.showRetrievedContent(data.id, data.content);
        });

        this.socket.on('retrieve_error', (data) => {
            this.showError(data.error);
        });

        this.socket.on('disconnect', (reason) => {
            this.cleanupTimers();
            
            if (reason === 'io server disconnect') {
                console.log('Disconnected by server');
                this.updateConnectionStatus('disconnected');
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

    setupFormHandlers() {
        // Simple CAPTCHA setup
        function generateCaptchaCode(length = 2) {
            const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
            let code = '';
            for (let i = 0; i < length; i++) {
                code += chars.charAt(Math.floor(Math.random() * chars.length));
            }
            return code;
        }

        let currentCaptcha = generateCaptchaCode();
        const captchaCodeDiv = document.getElementById('captcha-code');
        if (captchaCodeDiv) {
            captchaCodeDiv.textContent = currentCaptcha;
            captchaCodeDiv.style.userSelect = 'none';
            captchaCodeDiv.style.webkitUserSelect = 'none';
            captchaCodeDiv.style.MozUserSelect = 'none';
        }

        // Save form handler
        const saveForm = document.querySelector('#save-tab form');
        if (saveForm) {
            saveForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const textarea = saveForm.querySelector('textarea');
                const captchaInput = document.getElementById('captcha-input');
                if (!captchaInput || captchaInput.value.trim().toUpperCase() !== currentCaptcha) {
                    alert('CAPTCHA code incorrect. Please try again.');
                    // Regenerate code on failure
                    currentCaptcha = generateCaptchaCode();
                    if (captchaCodeDiv) captchaCodeDiv.textContent = currentCaptcha;
                    captchaInput.value = '';
                    return;
                }
                if (textarea && textarea.value.trim()) {
                    this.socket.emit('save_text', {
                        content: textarea.value,
                        captcha_input: captchaInput.value.trim().toUpperCase(),
                        captcha_code: currentCaptcha
                    });
                    // Regenerate code after submit
                    currentCaptcha = generateCaptchaCode();
                    if (captchaCodeDiv) captchaCodeDiv.textContent = currentCaptcha;
                    captchaInput.value = '';
                }
            });
        }

        // Retrieve CAPTCHA setup
        let currentCaptchaRetrieve = generateCaptchaCode();
        const captchaCodeDivRetrieve = document.getElementById('captcha-code-retrieve');
        if (captchaCodeDivRetrieve) {
            captchaCodeDivRetrieve.textContent = currentCaptchaRetrieve;
            captchaCodeDivRetrieve.style.userSelect = 'none';
            captchaCodeDivRetrieve.style.webkitUserSelect = 'none';
            captchaCodeDivRetrieve.style.MozUserSelect = 'none';
        }

        // Retrieve form handler
        const retrieveForm = document.querySelector('#retrieve-tab form');
        if (retrieveForm) {
            retrieveForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const input = retrieveForm.querySelector('input');
                const captchaInputRetrieve = document.getElementById('captcha-input-retrieve');
                if (!captchaInputRetrieve || captchaInputRetrieve.value.trim().toUpperCase() !== currentCaptchaRetrieve) {
                    alert('CAPTCHA code incorrect. Please try again.');
                    // Regenerate code on failure
                    currentCaptchaRetrieve = generateCaptchaCode();
                    if (captchaCodeDivRetrieve) captchaCodeDivRetrieve.textContent = currentCaptchaRetrieve;
                    captchaInputRetrieve.value = '';
                    return;
                }
                if (input && input.value.trim()) {
                    this.socket.emit('retrieve_text', {
                        lookup_id: input.value.trim(),
                        captcha_input: captchaInputRetrieve.value.trim().toUpperCase(),
                        captcha_code: currentCaptchaRetrieve
                    });
                    // Regenerate code after submit
                    currentCaptchaRetrieve = generateCaptchaCode();
                    if (captchaCodeDivRetrieve) captchaCodeDivRetrieve.textContent = currentCaptchaRetrieve;
                    captchaInputRetrieve.value = '';
                }
            });
        }

        // Character counter
        const textarea = document.querySelector('#save-tab textarea');
        if (textarea) {
            textarea.addEventListener('input', () => {
                const charCount = document.getElementById('charCount');
                if (charCount) {
                    charCount.textContent = textarea.value.length;
                }
            });
        }
    }

    showSaveSuccess(id, content) {
        const container = document.querySelector('.container');
        if (!container) return;

        // Remove any previous result cards (both .card and .container, but not the main .container)
        document.querySelectorAll('.card, .container.result').forEach(card => card.remove());

        const card = document.createElement('div');
        card.className = 'container result';
        card.innerHTML = `
            <h1>Text Stored Successfully!</h1>
            <div>You can use this ID to retrieve your text using the ''Retrieve Text'' tab:</div>
            <h2 class="card-content">${id}</h2>
        `;
        container.insertAdjacentElement('afterend', card);
    }

    showRetrievedContent(id, content) {
        const container = document.querySelector('.container');
        if (!container) return;

        // Remove any previous result cards (both .card and .container.result)
        document.querySelectorAll('.card, .container.result').forEach(card => card.remove());

        const card = document.createElement('div');
        card.className = 'container result';
        card.innerHTML = `
            <div>Text retrieved using ID: ${id}</div>
            <div class="card-content" id="retrieved-content">${content}</div>
            <button id="copy-btn" style="margin-top:1em; padding:0.5em 1.2em; font-size:1em; border-radius:6px; background:#6366f1; color:#fff; border:none; cursor:pointer;">Copy to Clipboard</button>
        `;
        container.insertAdjacentElement('afterend', card);
        // Add copy-to-clipboard functionality
        const copyBtn = card.querySelector('#copy-btn');
        const retrievedContent = card.querySelector('#retrieved-content');
        if (copyBtn && retrievedContent) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(retrievedContent.textContent)
                    .then(() => {
                        copyBtn.textContent = 'Copied!';
                        setTimeout(() => { copyBtn.textContent = 'Copy to Clipboard'; }, 1200);
                    })
                    .catch(() => {
                        copyBtn.textContent = 'Failed to copy';
                        setTimeout(() => { copyBtn.textContent = 'Copy to Clipboard'; }, 1200);
                    });
            });
        }
    }

    showError(message) {
        const container = document.querySelector('.container');
        if (!container) return;

        // Remove any previous result cards (both .card and .container.result)
        document.querySelectorAll('.card, .container.result').forEach(card => card.remove());

        const card = document.createElement('div');
        card.className = 'container result error-card';
        card.innerHTML = `
            <h1>Error</h1>    
            <h2>${message}</h2>
        `;
        container.insertAdjacentElement('afterend', card);
    }

    cleanupTimers() {
        clearTimeout(this.pingInterval);
        clearTimeout(this.connectionTimeout);
    }

    startConnectionTimer() {
        this.connectionTimeout = setTimeout(() => {
            console.log("Connection timeout - no response from server");
            this.updateConnectionStatus('reconnecting');
            this.socket.disconnect();
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
        
        statusElement.classList.remove(
            'connecting', 'connected', 'disconnected', 'reconnecting', 'error'
        );
        
        statusElement.classList.add(status);
        
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
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && (!this.socket || !this.socket.connected)) {
                this.connectSocket();
            }
        });

        const reconnectBtn = document.getElementById('reconnect-btn');
        if (reconnectBtn) {
            reconnectBtn.addEventListener('click', () => {
                this.reconnectAttempts = 0;
                if (this.socket) {
                    this.socket.disconnect();
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

    // Remove previous result cards when switching tabs
    document.querySelectorAll('.card, .container.result').forEach(card => card.remove());

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
document.addEventListener('DOMContentLoaded', () => {
    const socketManager = new SocketIOManager();
    window.socketManager = socketManager;
    
    const defaultTab = document.querySelector('.tab.active');
    if (defaultTab) {
        const tabId = defaultTab.dataset.tab || defaultTab.getAttribute('onclick').match(/'(.*?)'/)[1];
        switchTab(null, tabId);
    }
    
    const textareas = document.querySelectorAll('textarea[data-autoresize]');
    textareas.forEach(textarea => {
        autoResize(textarea);
        textarea.addEventListener('input', () => autoResize(textarea));
    });
    select_savetab = document.querySelector('#select_savetab');
    select_savetab.click();
});