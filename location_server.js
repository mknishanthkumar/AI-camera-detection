const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;
const DATA_DIR = path.join(__dirname, 'data');
const STATE_FILE = path.join(DATA_DIR, 'gps_state.json');

app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
}

// Initialize state file if not exists
if (!fs.existsSync(STATE_FILE)) {
    fs.writeFileSync(STATE_FILE, JSON.stringify({ lat: "", long: "", timestamp: "" }));
}

// Endpoint to update location
app.post('/api/location', (req, res) => {
    const { lat, long, timestamp } = req.body;

    const state = {
        lat: lat || "",
        long: long || "",
        timestamp: timestamp || new Date().toISOString()
    };

    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
    console.log(`[Location] Updated: ${state.lat}, ${state.long}`);
    res.json({ status: 'success', data: state });
});

app.listen(PORT, () => {
    console.log(`Location Server running at http://localhost:${PORT}`);
    console.log(`Open http://localhost:${PORT} in your browser to enable GPS.`);
});
