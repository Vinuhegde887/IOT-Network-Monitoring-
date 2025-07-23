from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
import json
import datetime
import os
import sys
import importlib.util
from shapely.ops import unary_union
from network_topology import NetworkTopology


# Create database if it doesn't exist
if not os.path.exists('network_data.db'):
    conn = sqlite3.connect('network_data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE network_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT,
            protocol TEXT DEFAULT 'TCP',
            rssi INTEGER,
            channel INTEGER,
            packets_total INTEGER,
            packets_lost INTEGER,
            latency REAL,
            throughput REAL,
            avg_latency REAL DEFAULT 0,
            avg_throughput REAL DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
else:
    # Add protocol column if it doesn't exist (for existing databases)
    conn = sqlite3.connect('network_data.db')
    c = conn.cursor()
    try:
        c.execute('ALTER TABLE network_metrics ADD COLUMN protocol TEXT DEFAULT "TCP"')
        c.execute('ALTER TABLE network_metrics ADD COLUMN avg_latency REAL DEFAULT 0')
        c.execute('ALTER TABLE network_metrics ADD COLUMN avg_throughput REAL DEFAULT 0')
        conn.commit()
        print("Added protocol and average metrics columns to existing database")
    except sqlite3.OperationalError:
        # Columns already exist
        pass
    conn.close()



import pandas as pd
import numpy as np
from sklearn.decomposition import TruncatedSVD
from statsmodels.tsa.arima.model import ARIMA
 # Keep your original metric list
metrics = ['rssi', 'latency', 'packet_loss', 'throughput']

# Load historical data once
historical_df = pd.read_csv("network_data.csv", parse_dates=['Timestamp'])
historical_df = historical_df.rename(columns={
    'RSSI (dBm)': 'rssi',
    'Latency (ms)': 'latency',
    'Packet Loss (%)': 'packet_loss',
    'Throughput (KB/s)': 'throughput'
})
historical_df = historical_df.set_index('Timestamp').sort_index()
historical_df = historical_df[metrics].resample('1min').mean().interpolate()
# Check if optimization module exists
optimization_spec = importlib.util.find_spec('optimization')
if optimization_spec is None:
    print("Warning: optimization.py module not found. Optimization features will be disabled.")
    # Create a simple mock module for optimization
    class MockOptimization:
        def optimize_channel_assignment(self):
            return {}
        def find_bottlenecks(self):
            return []
    optimization = MockOptimization()
else:
    import optimization

# Create a global instance of NetworkTopology
network_topology = NetworkTopology()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'network-monitoring-secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/api/data', methods=['POST'])
def receive_data():
    if not request.json:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    data = request.json
    protocol = data.get('protocol', 'TCP')
    node_id = data.get('node_id', 'unknown')

    print(f"Received {protocol} data from node: {node_id}")

    # Store in database
    conn = sqlite3.connect('network_data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO network_metrics 
        (node_id, protocol, rssi, channel, packets_total, packets_lost, latency, throughput, avg_latency, avg_throughput)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        node_id,
        protocol,
        data.get('rssi', 0),
        data.get('channel', 0),
        data.get('packets_total', 0),
        data.get('packets_lost', 0),
        data.get('latency', 0),
        data.get('throughput', 0),
        data.get('avg_latency', 0),
        data.get('avg_throughput', 0)
    ))
    conn.commit()
    conn.close()

    # Add timestamp for real-time data
    data['timestamp'] = datetime.datetime.now().isoformat()

    # 🔁 QoS Prediction using ARIMA + SVD
    try:
        # Compute packet loss %
        packet_loss = (
            data.get('packets_lost', 0) / max(data.get('packets_total', 1), 1)
        ) * 100

        # Predict QoS
        qos = evaluate_qos(
            rssi=data.get('rssi', -90),
            latency=data.get('latency', 999),
            packet_loss=packet_loss,
            throughput=data.get('throughput', 0)
        )
        data['qos'] = qos

    except Exception as e:
        print("QoS evaluation failed:", e)
        data['qos'] = "Unknown"
    
    # Broadcast to frontend
    socketio.emit('network_data', data)

    # Respond to sender (ESP32 or other)
    return jsonify({'status': 'ok','qos':qos})


@app.route('/api/history', methods=['GET'])
def get_history():
    hours = request.args.get('hours', 1, type=int)
    node_id = request.args.get('node_id', None)
    protocol = request.args.get('protocol', None)
    
    conn = sqlite3.connect('network_data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT * FROM network_metrics 
        WHERE timestamp >= datetime('now', '-' || ? || ' hours')
    '''
    params = [hours]
    
    if node_id:
        query += ' AND node_id = ?'
        params.append(node_id)
        
    if protocol:
        query += ' AND protocol = ?'
        params.append(protocol)
        
    query += ' ORDER BY timestamp DESC LIMIT 1000'
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    # Convert to list of dicts
    result = [dict(row) for row in rows]
    return jsonify(result)

@app.route('/api/protocols', methods=['GET'])
def get_protocols():
    """Get list of available protocols"""
    conn = sqlite3.connect('network_data.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT protocol FROM network_metrics WHERE protocol IS NOT NULL')
    protocols = [row[0] for row in c.fetchall()]
    conn.close()
    
    # Add default protocols if none exist
    if not protocols:
        protocols = ['HTTP', 'MQTT', 'UDP', 'TCP', 'ICMP', 'SMTP']
    
    return jsonify(protocols)

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    """Get list of available nodes"""
    conn = sqlite3.connect('network_data.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT node_id FROM network_metrics WHERE node_id IS NOT NULL')
    nodes = [row[0] for row in c.fetchall()]
    conn.close()
    
    return jsonify(nodes)

@app.route('/api/protocol-stats', methods=['GET'])
def get_protocol_stats():
    """Get aggregated statistics by protocol"""
    hours = request.args.get('hours', 24, type=int)
    
    conn = sqlite3.connect('network_data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT 
            protocol,
            COUNT(*) as count,
            AVG(latency) as avg_latency,
            AVG(throughput) as avg_throughput,
            AVG(CASE WHEN packets_total > 0 THEN (packets_lost * 100.0 / packets_total) ELSE 0 END) as avg_packet_loss,
            AVG(rssi) as avg_rssi,
            MIN(latency) as min_latency,
            MAX(latency) as max_latency,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen
        FROM network_metrics 
        WHERE timestamp >= datetime('now', '-' || ? || ' hours')
        AND protocol IS NOT NULL
        GROUP BY protocol
        ORDER BY count DESC
    '''
    
    c.execute(query, [hours])
    rows = c.fetchall()
    conn.close()
    
    result = [dict(row) for row in rows]
    return jsonify(result)

@app.route('/api/node-protocol-stats', methods=['GET'])
def get_node_protocol_stats():
    """Get statistics by node and protocol combination"""
    hours = request.args.get('hours', 24, type=int)
    
    conn = sqlite3.connect('network_data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT 
            node_id,
            protocol,
            COUNT(*) as count,
            AVG(latency) as avg_latency,
            AVG(throughput) as avg_throughput,
            AVG(CASE WHEN packets_total > 0 THEN (packets_lost * 100.0 / packets_total) ELSE 0 END) as avg_packet_loss,
            AVG(rssi) as avg_rssi,
            MAX(timestamp) as last_seen
        FROM network_metrics 
        WHERE timestamp >= datetime('now', '-' || ? || ' hours')
        AND protocol IS NOT NULL
        GROUP BY node_id, protocol
        ORDER BY node_id, protocol
    '''
    
    c.execute(query, [hours])
    rows = c.fetchall()
    conn.close()
    
    result = [dict(row) for row in rows]
    return jsonify(result)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Add new route for optimization
@app.route('/api/optimize', methods=['GET'])
def get_optimization():
    try:
        # Get channel optimization
        channel_assignments = optimization.optimize_channel_assignment()
        
        # Find bottlenecks
        bottlenecks = optimization.find_bottlenecks()
        
        return jsonify({
            'channel_assignments': channel_assignments,
            'bottlenecks': bottlenecks
        })
    except Exception as e:
        print(f"Optimization error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Add new dashboard page for optimization
@app.route('/optimization')
def optimization_dashboard():
    return render_template('optimization.html')

@app.route('/api/network/topology', methods=['GET'])
def get_network_topology():
    """Return the current network topology"""
    topology = network_topology.get_topology()
    return jsonify(topology)

@app.route('/api/network/routing', methods=['POST'])
def calculate_routing():
    """Calculate a path between two nodes"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    start_node = data.get('start_node')
    end_node = data.get('end_node')
    routing_algorithm = data.get('routing_algorithm', 'dijkstra')
    
    if not start_node or not end_node:
        return jsonify({'error': 'Start and end nodes are required'}), 400
    
    # Use your existing network_topology to calculate path
    result = network_topology.simulate_packet_transmission(
        start_node, end_node, routing_algorithm
    )
    
    return jsonify(result)

@app.route('/api/network/resilience', methods=['GET'])
def analyze_resilience():
    """Analyze network resilience"""
    # Import here to avoid circular imports
    from advanced_optimization import AdvancedNetworkOptimization
    
    # Create optimizer using network topology
    optimizer = AdvancedNetworkOptimization(network_topology)
    
    # Get resilience report
    resilience_report = optimizer.analyze_network_resilience()
    
    return jsonify(resilience_report)

@app.route('/api/network/failure-simulation', methods=['POST'])
def simulate_failure():
    """Simulate network failure scenarios"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    scenario = data.get('scenario', 'random')
    
    # Import here to avoid circular imports  
    from advanced_optimization import AdvancedNetworkOptimization
    
    # Create optimizer using network topology
    optimizer = AdvancedNetworkOptimization(network_topology)
    
    # Get failure report
    failure_report = optimizer.simulate_network_failure(scenario)
    
    return jsonify(failure_report)

@app.route('/api/network/routing-optimization', methods=['GET'])
def optimize_routing():
    """Optimize routing paths"""
    # Import here to avoid circular imports
    from advanced_optimization import AdvancedNetworkOptimization
    
    # Create optimizer using network topology
    optimizer = AdvancedNetworkOptimization(network_topology)
    
    # Get optimization report
    optimization_report = optimizer.optimize_routing_paths()
    
    return jsonify(optimization_report)

# Add a route for the network simulator UI
@app.route('/network-simulator')
def network_simulator():
    """Render the network simulator page"""
    return render_template('network-simulator.html')

# Protocol-specific endpoints for testing
@app.route('/api/test/http', methods=['POST'])
def test_http_endpoint():
    """Test endpoint for HTTP protocol testing"""
    data = request.json or {}
    return jsonify({'status': 'ok', 'protocol': 'HTTP', 'timestamp': datetime.datetime.now().isoformat()})

@app.route('/api/test/tcp', methods=['GET'])
def test_tcp_endpoint():
    """Test endpoint for TCP protocol testing"""
    return jsonify({'status': 'ok', 'protocol': 'TCP', 'timestamp': datetime.datetime.now().isoformat()})

# Handle WebSocket connections
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'msg': 'Connected to IoT Network Monitor'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_protocol_data')
def handle_protocol_data_request(data):
    """Handle request for specific protocol data"""
    protocol = data.get('protocol')
    node_id = data.get('node_id')
    hours = data.get('hours', 1)
    
    conn = sqlite3.connect('network_data.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    query = '''
        SELECT * FROM network_metrics 
        WHERE timestamp >= datetime('now', '-' || ? || ' hours')
    '''
    params = [hours]
    
    if protocol:
        query += ' AND protocol = ?'
        params.append(protocol)
    
    if node_id:
        query += ' AND node_id = ?'
        params.append(node_id)
    
    query += ' ORDER BY timestamp DESC LIMIT 100'
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    result = [dict(row) for row in rows]
    emit('protocol_data_response', result)
    
    




# QoS classification logic
def classify_qos(row):
    if row['latency'] < 50 and row['rssi'] > -60 and row['packet_loss'] < 1 and row['throughput'] > 100:
        return "High"
    elif row['latency'] > 150 or row['packet_loss'] > 5 or row['throughput'] < 30:
        return "Low"
    else:
        return "Medium"

# Main function: Takes new data point and returns predicted QoS
def evaluate_qos(rssi: float, latency: float, packet_loss: float, throughput: float) -> str:
    try:
        # Step 1: Append new data to historical
        new_row = pd.DataFrame([[rssi, latency, packet_loss, throughput]], columns=metrics)
        new_index = historical_df.index[-1] + pd.Timedelta(minutes=1)
        data = pd.concat([historical_df, pd.DataFrame(new_row.values, index=[new_index], columns=metrics)])

        # Step 2: SVD denoising
        svd = TruncatedSVD(n_components=2)
        reduced = svd.fit_transform(data)
        reconstructed = svd.inverse_transform(reduced)
        df_reconstructed = pd.DataFrame(reconstructed, columns=metrics, index=data.index)

        # Step 3: Forecast 1 step ahead using ARIMA for each metric
        forecast = {}
        for metric in metrics:
            series = df_reconstructed[metric]
            model = ARIMA(series, order=(2, 1, 2))
            model_fit = model.fit()
            forecast[metric] = model_fit.forecast(steps=1)[0]

        # Step 4: Classify QoS based on forecast
        forecast_series = pd.Series(forecast)
        qos_label = classify_qos(forecast_series)

        return qos_label

    except Exception as e:
        print("Error in QoS prediction:", e)
        return "Unknown"


if __name__ == '__main__':
    print("Starting Enhanced IoT Network Monitor Server...")
    print("Features:")
    print("- Multi-protocol support (HTTP, MQTT, UDP, TCP, ICMP, SMTP)")
    print("- Node selection and filtering")
    print("- Protocol-based performance analysis")
    print("- Real-time data visualization")
    print("- Historical data export")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
