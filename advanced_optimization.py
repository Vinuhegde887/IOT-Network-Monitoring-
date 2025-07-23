import networkx as nx
import random
import math
import json
from network_topology import NetworkTopology

class AdvancedNetworkOptimization:
    def __init__(self, network_topology):
        """
        Initialize optimization with existing network topology
        """
        self.topology = network_topology
        self.G = network_topology.G
    
    def analyze_network_resilience(self):
        """
        Analyze network resilience by calculating:
        1. Connectivity
        2. Node criticality
        3. Network diameter
        """
        resilience_report = {
            'is_connected': nx.is_connected(self.G),
            'connectivity': nx.node_connectivity(self.G),
            'network_diameter': nx.diameter(self.G),
            'critical_nodes': []
        }
        
        # Identify critical nodes using betweenness centrality
        betweenness_centrality = nx.betweenness_centrality(self.G, weight='weight')
        critical_threshold = sorted(betweenness_centrality.values(), reverse=True)[
            max(1, len(betweenness_centrality) // 4)
        ]
        
        resilience_report['critical_nodes'] = [
            {
                'node': node, 
                'centrality_score': score,
                'is_critical': score >= critical_threshold
            } 
            for node, score in betweenness_centrality.items()
        ]
        
        return resilience_report
    
    def optimize_routing_paths(self):
        """
        Optimize routing paths by:
        1. Finding alternative paths
        2. Calculating path redundancy
        3. Identifying potential bottlenecks
        """
        # Get all possible node pairs
        node_pairs = list(nx.non_edges(self.G))
        
        optimization_report = {
            'alternative_paths': [],
            'bottlenecks': [],
            'path_redundancy': []
        }
        
        # Find alternative paths and potential bottlenecks
        for start, end in [(n1, n2) for n1 in self.G.nodes() for n2 in self.G.nodes() if n1 != n2]:
            try:
                # Find all simple paths
                paths = list(nx.all_simple_paths(self.G, start, end, cutoff=5))
                
                if paths:
                    # Analyze paths
                    path_analysis = {
                        'start': start,
                        'end': end,
                        'total_paths': len(paths),
                        'paths': [],
                        'path_weights': []
                    }
                    
                    for path in paths:
                        # Calculate path weight
                        path_weight = sum(
                            self.G[path[i]][path[i+1]].get('weight', 1) 
                            for i in range(len(path)-1)
                        )
                        
                        path_analysis['paths'].append(path)
                        path_analysis['path_weights'].append(path_weight)
                    
                    optimization_report['alternative_paths'].append(path_analysis)
            except nx.NetworkXNoPath:
                continue
        
        # Identify bottlenecks using edge betweenness centrality
        edge_betweenness = nx.edge_betweenness_centrality(self.G, weight='weight')
        bottleneck_threshold = sorted(edge_betweenness.values(), reverse=True)[
            max(1, len(edge_betweenness) // 4)
        ]
        
        optimization_report['bottlenecks'] = [
            {
                'edge': edge, 
                'betweenness_score': score,
                'is_critical_bottleneck': score >= bottleneck_threshold
            } 
            for edge, score in edge_betweenness.items()
        ]
        
        return optimization_report
    
    def simulate_network_failure(self, failure_scenario='random'):
        """
        Simulate network failure scenarios
        """
        # Create a copy of the graph to simulate failures
        G_simulate = self.G.copy()
        
        if failure_scenario == 'random':
            # Randomly remove nodes or edges
            nodes_to_remove = random.sample(
                list(G_simulate.nodes()), 
                k=max(1, len(G_simulate.nodes()) // 4)
            )
            G_simulate.remove_nodes_from(nodes_to_remove)
        
        elif failure_scenario == 'targeted':
            # Remove most critical nodes
            betweenness = nx.betweenness_centrality(G_simulate)
            critical_nodes = sorted(
                betweenness.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:max(1, len(G_simulate.nodes()) // 5)]
            
            G_simulate.remove_nodes_from([node for node, _ in critical_nodes])
        
        # Analyze network after failure
        failure_report = {
            'scenario': failure_scenario,
            'removed_nodes': list(set(self.G.nodes()) - set(G_simulate.nodes())),
            'is_connected': nx.is_connected(G_simulate),
            'connected_components': list(nx.connected_components(G_simulate)),
            'remaining_connectivity': nx.node_connectivity(G_simulate)
        }
        
        return failure_report

def main():
    # Create network topology
    network_topology = NetworkTopology()
    
    # Initialize advanced optimization
    optimizer = AdvancedNetworkOptimization(network_topology)
    
    # Analyze network resilience
    print("Network Resilience Analysis:")
    resilience_report = optimizer.analyze_network_resilience()
    print(json.dumps(resilience_report, indent=2))
    
    # Optimize routing paths
    print("\nRouting Path Optimization:")
    routing_optimization = optimizer.optimize_routing_paths()
    print(json.dumps({
        'total_alternative_paths': len(routing_optimization['alternative_paths']),
        'total_bottlenecks': len(routing_optimization['bottlenecks'])
    }, indent=2))
    
    # Simulate network failures
    failure_scenarios = ['random', 'targeted']
    for scenario in failure_scenarios:
        print(f"\nNetwork Failure Simulation ({scenario} scenario):")
        failure_report = optimizer.simulate_network_failure(scenario)
        print(json.dumps(failure_report, indent=2))

if __name__ == '__main__':
    main()