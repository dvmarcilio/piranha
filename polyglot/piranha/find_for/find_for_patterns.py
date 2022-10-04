from dataclasses import dataclass
import datetime
import os
import subprocess
from polyglot_piranha import run_piranha_cli
import csv
import argparse
from time import perf_counter_ns


def nsecs_to_mins(ns: int) -> int:
    nsecs_to_secs = ns / 10**9
    return nsecs_to_secs / 60


def row_col(point) -> 'tuple[int, int]':
    return point.row, point.column


def distinct_elements_from_list(lst: 'list[any]'):
    # adding to a dict discards duplicates
    # dict maintains insertion order
    return list(dict.fromkeys(lst))


@dataclass(eq=True, frozen=True)
class CsvRow:
    """
    Defined to allow a csv row to be hashable; so it can be used in set's and map's.
    """
    path: str
    s_row: int
    s_col: int
    e_row: int
    e_col: int
    rule_name: str


def csv_rows_from_summary(summary) -> 'list[str]':
    rows = []
    distinct_rows: 'set[CsvRow]' = set()
    path = summary.path
    for match in summary.matches:
        rule_name = match[0]
        piranha_match = match[1]
        range = piranha_match.range
        s_row, s_col = row_col(range.start_point)
        e_row, e_col = row_col(range.end_point)
        csv_row = CsvRow(path, s_row, s_col, e_row, e_col, rule_name)
        if csv_row not in distinct_rows:
            rows.append([path, s_row, s_col, e_row, e_col, rule_name])
            distinct_rows.add(csv_row)

    return rows


def write_summaries_to_file(piranha_summary, output_file_path):
    with open(output_file_path, 'a+') as output_file:
        writer = csv.writer(output_file,
                            delimiter=',',
                            quotechar='"',
                            quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow([
            'file', 'start_row', 'start_col', 'end_row', 'end_col', 'rule_name'
        ])

        for summary in piranha_summary:
            summary_csv_rows = csv_rows_from_summary(summary)
            for csv_row in summary_csv_rows:
                writer.writerow(csv_row)


def unique_file_paths_from_summary(piranha_summary) -> 'list[str]':
    non_unique_file_paths = [summary.path for summary in piranha_summary]
    return distinct_elements_from_list(non_unique_file_paths)


def collect_paths_from_csv(csv_path: str) -> 'list[str]':
    paths: 'list[str]' = []
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            paths.append(row[0])
    return distinct_elements_from_list(paths)


def run_and_write_for_base_pattern() -> 'list[str]':
    """
    Runs `find_for` rule for the entire codebase given as argument.
    """
    if os.path.exists(base_output_file_path):
        print("Skipping execution for base rule as csv already exists.",
              flush=True)
        return collect_paths_from_csv(base_output_file_path)

    print('Executing for base rule', flush=True)
    config_path = os.path.join(base_path, 'configurations/')

    piranha_summary = run_piranha_cli(codebase_path,
                                      config_path,
                                      should_rewrite_files=False)

    write_summaries_to_file(piranha_summary, base_output_file_path)

    return unique_file_paths_from_summary(piranha_summary)


def run_and_write_for_pattern(pattern_dir: str,
                              file_paths_with_for_loop: 'list[str]'):
    output_file_path = base_output_path + pattern_dir + '.csv'
    if os.path.exists(output_file_path):
        # skip running if file for pattern exists
        print(f"Skipping execution for '{pattern_dir}' as csv already exists.",
              flush=True)
        return

    print(f"Running for '{pattern_dir}'", flush=True)

    summaries = []
    config_path = os.path.join(base_path, pattern_dir, 'configurations/')
    for file_path_with_for_loop in file_paths_with_for_loop:
        file_piranha_summary = run_piranha_cli(file_path_with_for_loop,
                                               config_path,
                                               should_rewrite_files=False)
        for summary in file_piranha_summary:
            summaries.append(summary)

    write_summaries_to_file(summaries, output_file_path)


### Script execution
start_time = perf_counter_ns()

parser = argparse.ArgumentParser()
parser.add_argument('codebase_path', type=str)
parser.add_argument('output_path', type=str, nargs="?")
args = parser.parse_args()

base_path = os.path.join(os.path.dirname(__file__))
codebase_path = args.codebase_path

base_output_path = ''
if not args.output_path:
    time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base_output_path = os.path.join(base_path, 'output_' + time_str + '/')
else:
    base_output_path = os.path.abspath(args.output_path) + '/'

if not os.path.exists(base_output_path):
    os.mkdir(base_output_path)

print(f'base output path: {base_output_path}', flush=True)

base_output_file_path = base_output_path + '1_for_loops.csv'
revision_file_path = base_output_path + 'revision.txt'
with open(revision_file_path, 'w+') as f:
    rev = subprocess.check_output(cwd=os.path.dirname(codebase_path),
                                  args=['git', 'rev-parse',
                                        'HEAD']).decode('ascii').strip()
    f.write(rev)

file_paths_with_for_loop = run_and_write_for_base_pattern()

pattern_directories = [
    '2_any_go_stmt_in_for',
    '3_only_go_stmt',
    '4_surrounded_go_stmt',
    '5_var_decl_before_go_stmt',
    '6_var_decl_before_surrounded_go_stmt',
]

for pattern_dir in pattern_directories:
    run_and_write_for_pattern(pattern_dir, file_paths_with_for_loop)

stop_time = perf_counter_ns()
elapsed_time_ns = (stop_time - start_time)
time_file_path = base_output_path + 'time.txt'
with open(time_file_path, 'w+') as f:
    f.write(f'{nsecs_to_mins(elapsed_time_ns)} minutes')
