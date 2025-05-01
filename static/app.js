// In your static JavaScript file
let socket;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
const reconnectDelay = 1000; // 1 second

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocol + window.location.host + '/ws/row-count';
    
    socket = new WebSocket(wsUrl);

    socket.onopen = function(e) {
        console.log("WebSocket connected");
        reconnectAttempts = 0; // Reset on successful connection
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'count_update') {
            updateCountDisplay(data.count);
        }
    };

    socket.onclose = function(event) {
        if (event.wasClean) {
            console.log(`WebSocket closed cleanly, code=${event.code}, reason=${event.reason}`);
        } else {
            console.log('WebSocket connection died');
            attemptReconnect();
        }
    };

    socket.onerror = function(error) {
        console.log(`WebSocket error: ${error.message}`);
        socket.close();
    };
}

function attemptReconnect() {
    if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        console.log(`Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts})...`);
        setTimeout(connectWebSocket, reconnectDelay * reconnectAttempts);
    } else {
        console.log('Max reconnection attempts reached');
    }
}

function updateCountDisplay(count) {
    // Update your UI with the new count
    const countElement = document.getElementById('row-count');
    if (countElement) {
        countElement.textContent = `Total rows: ${count}`;
        
        // Optional: Add visual feedback
        countElement.classList.add('updated');
        setTimeout(() => countElement.classList.remove('updated'), 500);
    }
}

// Start the connection when page loads
document.addEventListener('DOMContentLoaded', connectWebSocket);

// Optional: Send periodic pings to keep connection alive
setInterval(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send('ping');
    }
}, 30000); // Every 30 seconds


function autoResize(textarea) {
    textarea.style.height = 'auto'; // Reset height
    textarea.style.height = textarea.scrollHeight + 'px'; // Set to full scroll height
}

function updateCount() {
    const count = document.getElementById('content').value.length;
    document.getElementById('charCount').innerText = count;
}
