import os
import json
import argparse
import glob
import sys

from analysis_dataclasses import FuncLiteral, Pattern, Range, dataclass_from_dict

# Python >= 3.9 has removeprefix
def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text

parser = argparse.ArgumentParser()
parser.add_argument('output_path', type=str)
parser.add_argument('--sourcegraph-url', type=str, default='', dest='sourcegraph_url')
parser.add_argument('--prefix-to-remove', type=str, default='/home/user/go-code/', dest='prefix_to_remove')
args = parser.parse_args()

base_output_path = os.path.abspath(args.output_path) + '/'
matches_path = base_output_path + 'matches/'

print(f'base output path: {base_output_path}', flush=True)

basic: 'list[Pattern]' = []
a1: 'list[Pattern]' = []
a2: 'list[Pattern]' = []

for json_file_path in glob.glob(matches_path + '/*.json'):
    with open(json_file_path) as file:
        patterns_dict = json.load(file)
        for p in patterns_dict:
            pattern: Pattern = dataclass_from_dict(Pattern, p)
            if pattern.name == 'basic':
                basic.append(pattern)
            elif pattern.name == 'advanced1':
                a1.append(pattern)
            elif pattern.name == 'advanced2':
                a2.append(pattern)

total = len(basic) + len(a1) + len(a2)

def sourcegraphify(file_path: str, pattern: Pattern) -> 'list[str]':
    file_url = remove_prefix(file_path, args.prefix_to_remove)
    url = args.sourcegraph_url + file_url
    urls: 'list[str]' = []
    for func_literal_dict in pattern.m_decl.func_literals:
        func_literal = dataclass_from_dict(FuncLiteral, func_literal_dict)
        suffix = '?subtree=true#L' + str(func_literal.start_line())
        urls.append(url + suffix)

    return urls

def channel_receive_lines(pattern: Pattern) -> 'list[int]':
    lines: 'list[int]' = []
    for ch_receive_range_dict in pattern.m_decl.channel_receive_after:
        rg: Range = dataclass_from_dict(Range, ch_receive_range_dict)
        lines.append(rg.start_line())

    return lines

with open(base_output_path + 'summary.txt', 'w') as summary_f:

    sys.stdout = summary_f

    print(f'Total patterns: {total}\n')

    def print_pattern(name: str, patterns: 'list[Pattern]'):
        print(f'# {name}: {len(patterns)}')
        for p in patterns:
            print()
            file_path: str = p.m_decl.file
            print(f'    file: {file_path}')
            print(f'    func line: {p.m_decl.start_line()}')
            print(f'    channel receive lines: {channel_receive_lines(p)}')
            if args.sourcegraph_url:
                print('    func literals:')
                for url in sourcegraphify(file_path, p):
                    print(f'        {url}')

        print()

    print_pattern('basic', basic)
    print_pattern('advanced1', a1)
    print_pattern('advanced2', a2)
