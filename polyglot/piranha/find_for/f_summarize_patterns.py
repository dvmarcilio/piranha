import argparse
import os
import json
import glob
import sys

from f_dataclasses import Pattern, dataclass_from_dict


def remove_prefix(text, prefix):
    # Python >= 3.9 has removeprefix
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def paths_in_txt(path: str) -> 'list[str]':
    paths: 'list[str]' = []
    with open(base_path + '/' + path, 'r') as f:
        paths = [p.rstrip() for p in f]
    return paths


paths: 'list[str]' = []

parser = argparse.ArgumentParser()
parser.add_argument('--test_paths', action='store_true', default=False)
args = parser.parse_args()


base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
base_path = os.path.join(base_path, 'f-calls-checker/')
matches_path = os.path.join(base_path, 'matches/')

if args.test_paths:
    paths = paths_in_txt(
        'paths_test.txt') + paths_in_txt('paths_test_no_import.txt')
    matches_path += 'tests/'
    print('Running for test Paths')
else:
    print('*Not* running for test paths')
    matches_path += 'non-tests/'
    paths = paths_in_txt(
        'paths.txt') + paths_in_txt('paths_no_import.txt')


count_by_pattern: 'dict[str, int]' = {}
total = 0
distinct_files: 'set[str]' = set()

for json_file_path in glob.glob(matches_path + '/*.json'):
    with open(json_file_path) as file:
        patterns_dict = json.load(file)
        for p in patterns_dict:
            pattern: Pattern = dataclass_from_dict(Pattern, p)
            count_by_pattern[pattern.name] = count_by_pattern.get(
                pattern.name, 0) + 1
            total += 1
            distinct_files.add(pattern.file)

# descending order by count
count_by_pattern = dict(sorted(count_by_pattern.items(),
                        key=lambda item: item[1], reverse=True))

print(f'total files: {len(distinct_files):,}')
print(f'total patterns: {total:,}\n')
for pattern_name, count in count_by_pattern.items():
    pct = (count / float(total)) * 100
    print(f'- {pattern_name}: {count:,} ({pct:.2f}%)')

print()
print('Paths with `GetBoolValue(` but nothing found:\n')
for path in paths:
    if not path in distinct_files:
        print(path)
