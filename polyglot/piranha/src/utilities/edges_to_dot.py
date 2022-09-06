# pip install -m toml

import toml
from dataclasses import dataclass

@dataclass
class Edge:
    to: str
    scope: str

# TODO: take files as argument
rules_file = '../cleanup_rules/java/rules.toml'
rules_toml_dict = toml.load(rules_file)
rules_by_group_dict: dict[str, list[str]] = {}

for rule_toml in rules_toml_dict['rules']:
    if 'groups' in rule_toml:
        rule_name: str = rule_toml['name']
        for group_name in rule_toml['groups']:
            if group_name in rules_by_group_dict:
                rules_by_group_dict[group_name].append(rule_name) 
            else:
                rules_by_group_dict[group_name] = [rule_name]

for item in rules_by_group_dict.items():
    print(item)

edges_file = '../cleanup_rules/java/edges.toml'
edges_toml_dict = toml.load(edges_file)
# dict's are ordered
graph_dict: dict[str, list[Edge]] = {}

for edge_toml in edges_toml_dict['edges']:
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
    if node in rules_by_group_dict:
        node_label = '[shape=record label="' +  node + '\\n\\n' + '\\n'.join(rules_by_group_dict[node]) + '"]'
        dot_lines.append(f'   {node} {node_label}')
    else: # a rule not in a group 
        dot_lines.append('  '  + node)

dot_lines.append('\n')

for node, edges in graph_dict.items():
    for edge in edges:
        dot_lines.append('  ' + f'{node} -> {edge.to} [label="{edge.scope}"]')

dot_lines.append('\n}')

# can be fed to: https://dreampuf.github.io/GraphvizOnline
print('\n'.join(dot_lines))
