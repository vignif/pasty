
function autoResize(textarea) {
    textarea.style.height = 'auto'; // Reset height
    textarea.style.height = textarea.scrollHeight + 'px'; // Set to full scroll height
}

function updateCount() {
    const count = document.getElementById('content').value.length;
    document.getElementById('charCount').innerText = count;
}

function switchTab(event, tabId) {
    // Remove 'active' class from all tabs
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Add 'active' class to the clicked tab
    event.target.classList.add('active');

    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.classList.remove('active'));

    // Show the clicked tab's content
    document.getElementById(tabId).classList.add('active');
}

let lastRowCount = null;

async function updateRowCount() {
    try {
        const response = await fetch('/api/count');
        const data = await response.json();
        if (data.count !== lastRowCount) {
            lastRowCount = data.count;
            document.getElementById('row-count').innerText = `Total rows: ${data.count}`;
        }
    } catch (err) {
        console.error('Failed to fetch row count:', err);
    }
}

// Initial call
updateRowCount();

// Poll every 10 seconds (instead of every second)
// setInterval(updateRowCount, 1000);


// WebSocket connection
const socket = new WebSocket('ws://127.0.0.1:8000/ws/row-count');  // Update URL if using production

socket.onopen = function() {
    console.log("WebSocket connection established.");
};

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);  // Parse the JSON string
    console.log("Received row count:", data.count);  // Access the integer value

    document.getElementById('row-count').innerText = `Total rows: ${data.count}`;
};

socket.onerror = function(error) {
    console.log("WebSocket error:", error);
};

socket.onclose = function() {
    console.log("WebSocket connection closed.");
};
