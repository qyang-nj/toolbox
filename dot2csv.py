#!/usr/bin/env python3

"""
This script reads a DOT graph from stdin and converts it to two CSV files: nodes.csv and edges.csv,
which can be imported into Gephi for visualization.

Usage:
  bazel query --output=graph --notool_deps "{query_strin}" | dot2csv.py
"""

import csv
import sys
import pydot

MODULE_SUFFIXES = [
    "Library",
    "Demo",
    "Plugin",
    "Feature",
    "PrivateUI",
    "Service",
    "FeatureInterface",
    "ServiceInterface",
    "ServiceAdapter",
    "SharedUI",
    "CoreUI",
    "Foundation"
]


class Node:
    def __init__(self, node_id: str):
        self.node_id = node_id.strip('"')
        # Bazel query may put multiple targets in the same node
        self.targets = self.node_id.split("\\n")

    def label(self) -> str:
        """The display name of the node, e.g. MyFeature"""
        if len(self.targets) == 1:
            return self.node_id.split(":")[1]
        else:
            return f"Multiple({", ".join([t.split(":")[1] for t in self.targets])})"

    def type(self) -> str:
        """The type of the node, e.g. Feature, Service, etc."""
        if len(self.targets) == 1:
            for suffix in MODULE_SUFFIXES:
                if self.node_id.endswith(suffix):
                    return suffix
            return "ThirdParty"
        else:
            return "MultipleTargets"


def write_to_csv(nodes, edges, nodes_file='nodes.csv', edges_file='edges.csv'):
    try:
        with open(nodes_file, 'w', newline='', encoding='utf-8') as nodes_csv:
            csvwriter = csv.writer(nodes_csv)
            csvwriter.writerow(['ID', 'Label', 'Type'])
            csvwriter.writerows(nodes)

        with open(edges_file, 'w', newline='', encoding='utf-8') as edges_csv:
            csvwriter = csv.writer(edges_csv)
            csvwriter.writerow(['Source', 'Target'])
            csvwriter.writerows(edges)

    except Exception as e:
        print(f"❌ Error writing CSV files: {e}")


def main():
    dot_content = sys.stdin.read()
    graphs = pydot.graph_from_dot_data(dot_content)
    if not graphs:
        print("❌ No graph found in the input.")
        return

    graph = graphs[0]

    nodes = []
    for node in graph.get_nodes():
        name = node.get_name()
        if name == "node":
            # Skip the dot default node
            continue
        node = Node(name)
        nodes.append([node.node_id, node.label(), node.type()])

    edges = []
    for edge in graph.get_edges():
        src = edge.get_source()
        tgt = edge.get_destination()
        edges.append([Node(src).node_id, Node(tgt).node_id])

    write_to_csv(nodes, edges)


if __name__ == "__main__":
    main()
