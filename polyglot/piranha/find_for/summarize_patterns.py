import os
import json
import argparse
import glob
import sys

from analysis_dataclasses import Pattern, dataclass_from_dict

parser = argparse.ArgumentParser()
parser.add_argument('output_path', type=str)
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

with open(base_output_path + 'summary.txt', 'w') as summary_f:

    sys.stdout = summary_f

    print(f'Total patterns: {total}\n')

    def print_pattern(name: str, patterns: 'list[Pattern]'):
        print(f'# {name}: {len(patterns)}')
        for p in patterns:
            print()
            print(f'    file: {p.m_decl.file}')
            print(f'    func line: {p.m_decl.start_line()}')

        print()

    print_pattern('basic', basic)
    print_pattern('advanced1', a1)
    print_pattern('advanced2', a2)
