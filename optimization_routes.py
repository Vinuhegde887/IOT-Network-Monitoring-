from flask import jsonify, request
from network_topology import NetworkTopology
from advanced_optimization import AdvancedNetworkOptimization
import json

# Initialize network topology and optimization
network_topology = NetworkTopology()
network_optimizer = AdvancedNetworkOptimization(network_topology)

def register_optimization_routes(app):
    """
    Register additional optimization-related routes
    """
    @app.route('/api/network/resilience', methods=['GET'])
    def get_network_resilience():
        """
        Endpoint to get network resilience analysis
        """
        try:
            resilience_report = network_optimizer.analyze_network_resilience()
            return jsonify(resilience_report)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/network/routing-optimization', methods=['GET'])
    def get_routing_optimization():
        """
        Endpoint to get routing path optimization details
        """
        try:
            routing_optimization = network_optimizer.optimize_routing_paths()
            return jsonify(routing_optimization)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/network/failure-simulation', methods=['POST'])
    def simulate_network_failure():
        """
        Endpoint to simulate network failure scenarios
        """
        try:
            # Get scenario from request, default to 'random'
            scenario = request.json.get('scenario', 'random')
            
            # Validate scenario
            allowed_scenarios = ['random', 'targeted']
            if scenario not in allowed_scenarios:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid scenario. Allowed scenarios: {allowed_scenarios}'
                }), 400
            
            # Simulate network failure
            failure_report = network_optimizer.simulate_network_failure(scenario)
            return jsonify(failure_report)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/network/routing', methods=['POST'])
    def simulate_packet_routing():
        """
        Endpoint to simulate packet routing between nodes
        """
        try:
            # Get routing parameters from request
            data = request.json
            start_node = data.get('start_node')
            end_node = data.get('end_node')
            routing_algorithm = data.get('routing_algorithm', 'dijkstra')
            
            # Validate input
            if not start_node or not end_node:
                return jsonify({
                    'status': 'error',
                    'message': 'Start and end nodes are required'
                }), 400
            
            # Allowed routing algorithms
            allowed_algorithms = ['dijkstra', 'distance_vector', 'link_state']
            if routing_algorithm not in allowed_algorithms:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid routing algorithm. Allowed: {allowed_algorithms}'
                }), 400
            
            # Simulate packet transmission
            routing_result = network_topology.simulate_packet_transmission(
                start_node, 
                end_node, 
                routing_algorithm
            )
            
            return jsonify(routing_result)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/network/topology', methods=['GET'])
    def get_network_topology():
        """
        Endpoint to get detailed network topology information
        """
        try:
            topology_details = network_topology.get_network_graph_details()
            return jsonify(topology_details)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

# This function should be called in app.py after creating the Flask app
# app = Flask(__name__)
# register_optimization_routes(app)