from collections import namedtuple
from re import L
from typing import OrderedDict
import toml
from dataclasses import dataclass

@dataclass
class Edge:
    to: str
    scope: str

# TODO: take file as argument
f = '../cleanup_rules/java/edges.toml'

edges_dict = toml.load(f)

# dict's are ordered
graph_dict: dict[str, list[Edge]] = {}

for edge_toml in edges_dict['edges']:
    from_node = edge_toml['from']
    to_nodes: list[str] = edge_toml['to']
    scope = edge_toml['scope']
    for to_node in to_nodes:
        edge = Edge(to = to_node, scope = scope)
        if from_node in graph_dict:
            graph_dict[from_node].append(edge)
        else:
            graph_dict[from_node] = [edge]

for item in graph_dict.items():
    print(item)

dot_lines: list[str] = []
dot_lines.append('digraph {\n')

for node in graph_dict.keys():
    dot_lines.append('  '  + node)

dot_lines.append('\n')

for node, edges in graph_dict.items():
    for edge in edges:
        dot_lines.append('  ' + f'{node} -> {edge.to} [label="{edge.scope}"]')


dot_lines.append('\n}')

print('\n'.join(dot_lines))