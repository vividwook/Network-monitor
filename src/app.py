from flask import Flask, render_template, jsonify
from monitor import load_devices, poll_device
import logging

app = Flask(__name__)
devices = load_devices()

@app.route('/')
def home():
    statuses = []
    for device in devices:
        status = poll_device(device)
        statuses.append({**device, **status})
    return render_template('dashboard.html', statuses=statuses)

@app.route('/api/status')
def api_status():
    statuses = []
    for device in devices:
        status = poll_device(device)
        statuses.append({**device, **status})
    return jsonify(statuses)

if __name__ == '__main__':
    app.run(debug=True)
