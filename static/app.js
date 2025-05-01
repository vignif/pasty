let socket;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 1000;

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + window.location.host + '/ws/row-count';
    
    socket = new WebSocket(wsUrl);

    socket.onopen = function(e) {
        console.log("WebSocket connected");
        reconnectAttempts = 0;
        // Send initial ping to verify connection
        sendPing();
    };

    socket.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            
            if (data.type === 'count_update') {
                updateCountDisplay(data.count);
            } else if (data.type === 'pong') {
                console.log("Heartbeat acknowledged");
                // Schedule next ping
                setTimeout(sendPing, 25000);
            }
        } catch (e) {
            console.log("Received non-JSON message:", event.data);
        }
    };

    socket.onclose = function(event) {
        if (event.wasClean) {
            console.log(`Connection closed cleanly`);
        } else {
            console.log('Connection died');
            attemptReconnect();
        }
    };

    socket.onerror = function(error) {
        console.log(`WebSocket error:`, error);
        socket.close();
    };
}

function sendPing() {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: "ping" }));
    }
}

function attemptReconnect() {
    if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        console.log(`Reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`);
        setTimeout(connectWebSocket, reconnectDelay * reconnectAttempts);
    } else {
        console.log('Max reconnection attempts reached');
    }
}

function updateCountDisplay(count) {
    const countElement = document.getElementById('row-count');
    if (countElement) {
        countElement.textContent = count;
        countElement.classList.add('updated');
        setTimeout(() => countElement.classList.remove('updated'), 500);
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto'; // Reset height
    textarea.style.height = textarea.scrollHeight + 'px'; // Set to full scroll height
}


// Initialize connection when page loads
document.addEventListener('DOMContentLoaded', connectWebSocket);