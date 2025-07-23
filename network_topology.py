import networkx as nx
import numpy as np
import random
import json
import heapq

class NetworkTopology:
    def __init__(self):
        # Create a graph representing the network topology
        self.G = nx.Graph()
        self.setup_network_topology()
        
    def setup_network_topology(self):
        """
        Create network topology based on the provided network diagram
        Nodes will be added with their IP addresses
        """
        # Routers
        routers = [
            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 
            'R6', 'R7', 'Router-1', 'Router-2'
        ]
        
        # Subnets / Buildings
        subnets = [
            'Building1', 'Building2', 'Building3', 'Building4',
            'Server1', 'Server2', 'Wireless-Router'
        ]
        
        # Add routers
        for router in routers:
            self.G.add_node(router, type='router')
        
        # Add subnets
        for subnet in subnets:
            self.G.add_node(subnet, type='subnet')
        
        # Add links with weights (representing distance or cost)
        links = [
            ('R0', 'Building1', 10),
            ('R1', 'Building2', 15),
            ('R2', 'Building3', 12),
            ('R3', 'Building4', 18),
            ('R4', 'Wireless-Router', 8),
            
            # Router interconnections
            ('R0', 'R1', 20),
            ('R1', 'R2', 25),
            ('R2', 'R3', 22),
            ('R3', 'R4', 30),
            ('R4', 'R0', 35),
            
            # Additional interconnections
            ('Router-1', 'R0', 5),
            ('Router-2', 'R2', 7),
            ('Server1', 'R1', 6),
            ('Server2', 'R3', 9)
        ]
        
        # Add weighted edges
        for start, end, weight in links:
            self.G.add_edge(start, end, weight=weight)
    
    def dijkstra_routing(self, start, end):
        """
        Implement Dijkstra's shortest path routing algorithm
        """
        try:
            path = nx.dijkstra_path(self.G, start, end, weight='weight')
            path_length = nx.dijkstra_path_length(self.G, start, end, weight='weight')
            return {
                'path': path,
                'total_cost': path_length
            }
        except nx.NetworkXNoPath:
            return {
                'path': None,
                'total_cost': float('inf')
            }
    
    def distance_vector_routing(self, start, end):
        """
        Simulate Distance Vector Routing Algorithm
        """
        # Create routing table
        routing_table = {}
        nodes = list(self.G.nodes())
        
        # Initialize routing table
        for node in nodes:
            routing_table[node] = {
                'distance': float('inf'),
                'next_hop': None
            }
        routing_table[start]['distance'] = 0
        
        # Bellman-Ford like iterations
        for _ in range(len(nodes) - 1):
            for node in nodes:
                for neighbor in self.G.neighbors(node):
                    edge_weight = self.G[node][neighbor].get('weight', 1)
                    
                    # Update distance if a shorter path is found
                    if (routing_table[node]['distance'] + edge_weight < 
                        routing_table[neighbor]['distance']):
                        routing_table[neighbor]['distance'] = (
                            routing_table[node]['distance'] + edge_weight
                        )
                        routing_table[neighbor]['next_hop'] = node
        
        # Reconstruct path
        path = []
        current = end
        while current != start:
            path.insert(0, current)
            current = routing_table[current]['next_hop']
            if current is None:
                return {
                    'path': None,
                    'total_cost': float('inf')
                }
        path.insert(0, start)
        
        return {
            'path': path,
            'total_cost': routing_table[end]['distance']
        }
    
    def link_state_routing(self, start, end):
        """
        Simulate Link State Routing Algorithm (Dijkstra-based)
        """
        # Create a link state database (graph representation)
        link_state_db = nx.Graph(self.G)
        
        # Use Dijkstra's algorithm from networkx
        try:
            path = nx.dijkstra_path(link_state_db, start, end, weight='weight')
            path_length = nx.dijkstra_path_length(link_state_db, start, end, weight='weight')
            return {
                'path': path,
                'total_cost': path_length,
                'link_state_db': list(link_state_db.edges(data=True))
            }
        except nx.NetworkXNoPath:
            return {
                'path': None,
                'total_cost': float('inf'),
                'link_state_db': []
            }
    
    def simulate_packet_transmission(self, start, end, routing_algorithm='dijkstra'):
        """
        Simulate packet transmission between start and end nodes
        """
        # Select routing algorithm
        if routing_algorithm == 'dijkstra':
            routing_result = self.dijkstra_routing(start, end)
        elif routing_algorithm == 'distance_vector':
            routing_result = self.distance_vector_routing(start, end)
        elif routing_algorithm == 'link_state':
            routing_result = self.link_state_routing(start, end)
        else:
            raise ValueError("Invalid routing algorithm")
        
        # Simulate packet transmission
        if routing_result['path'] is None:
            return {
                'status': 'failure',
                'message': 'No path found',
                'routing_details': routing_result
            }
        
        # Add some randomness to simulate real-world conditions
        packet_loss_prob = random.uniform(0.01, 0.1)
        transmission_delay = sum(
            self.G[routing_result['path'][i]][routing_result['path'][i+1]].get('weight', 1) 
            for i in range(len(routing_result['path'])-1)
        )
        
        return {
            'status': 'success',
            'path': routing_result['path'],
            'total_cost': routing_result['total_cost'],
            'packet_loss_probability': packet_loss_prob,
            'transmission_delay': transmission_delay,
            'routing_algorithm': routing_algorithm
        }
    
    def get_network_graph_details(self):
        """
        Return detailed information about the network graph
        """
        return {
            'nodes': list(self.G.nodes(data=True)),
            'edges': list(self.G.edges(data=True)),
            'total_nodes': self.G.number_of_nodes(),
            'total_edges': self.G.number_of_edges()
        }

# Example usage
def main():
    # Create network topology
    network = NetworkTopology()
    
    # Simulate packet transmission
    start_node = 'R0'
    end_node = 'Building3'
    
    # Try different routing algorithms
    routing_algorithms = ['dijkstra', 'distance_vector', 'link_state']
    
    for algo in routing_algorithms:
        print(f"\nRouting Algorithm: {algo}")
        result = network.simulate_packet_transmission(start_node, end_node, algo)
        print(json.dumps(result, indent=2))
    
    # Get network graph details
    network_details = network.get_network_graph_details()
    print("\nNetwork Graph Details:")
    print(json.dumps(network_details, indent=2))

if __name__ == '__main__':
    main()