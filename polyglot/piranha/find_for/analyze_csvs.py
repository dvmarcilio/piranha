import argparse
import os
import pandas as pd

# python3 -m pip install pandas


def csv_path(pattern):
    return os.path.join(base_output_path, pattern + '.csv')


def pattern_over_total_loops(pattern, total_loops,
                             total_distinct_files_with_loops):
    csv_p = csv_path(pattern)
    if not os.path.exists(csv_p):
        print(f"\n'{csv_p}' does not exist.")
        return

    pattern_csv = pd.read_csv(csv_p, delimiter=',')
    total = len(pattern_csv)
    print(f'\n#{pattern}: {total}')
    total_tests = len(pattern_csv[pattern_csv['file'].str.endswith('_test.go')])
    test_pct = (total_tests / float(total)) * 100
    print(f'    total in test files: {total_tests} ({test_pct:.2f}%)')
    print()

    pct_total = (total / float(total_loops)) * 100
    print(f'    {pct_total:.2f}% of total `for_stmt`')

    distinct_files_df = pattern_csv['file'].unique()
    distinct_files = len(distinct_files_df)
    print(f'    distinct files: {distinct_files:,}')

    pct_distinct = (distinct_files /
                    float(total_distinct_files_with_loops)) * 100
    print(f'    {pct_distinct:.2f}% of total distinct files with `for_stmt`')


def print_intersection(superset_csv, subset_csv, msg):
    intersection = pd.merge(superset_csv, subset_csv, on=["file","start_row","start_col","end_row","end_col"], how='right')
    # quickly hacked intersection. the 'join' can give more values than the subset length
    if len(intersection) >= len(subset_csv):
        print('\n' + msg)
        pct = (len(subset_csv) / float(len(superset_csv))) * 100
        print(f'    {pct:.2f}% of the superset')

parser = argparse.ArgumentParser()
parser.add_argument('output_path', type=str)
args = parser.parse_args()

patterns = [
    '1_for_loops',
    '2_any_go_stmt_in_for',
    '3_only_go_stmt',
    '4_surrounded_go_stmt',
    '5_var_decl_before_go_stmt',
    '6_var_decl_before_surrounded_go_stmt',
]

# Properly use this
def total_tests_and_pct(df) -> 'tuple[int, int]':
    total_df = len(df)
    test_files_df = df[df['file'.str.endswith('_test.go')]]
    total_test_files = len(test_files_df)
    test_pct = (total_test_files / float(total_df)) * 100
    return total_test_files, test_pct

base_output_path = os.path.abspath(args.output_path) + '/'

# using pandas for simplicity w/ csv
path_0 = csv_path(patterns[0])
for_loops_csv = pd.read_csv(path_0, delimiter=',')
total_loops = len(for_loops_csv)
print('# For statements')
print(f'    total loops: {total_loops:,}')

loops_in_tests_df = for_loops_csv[for_loops_csv['file'].str.endswith('_test.go')]
total_loops_in_test = len(loops_in_tests_df)
test_pct = (total_loops_in_test / float(total_loops)) * 100
print(f'    total in test files: {total_loops_in_test} ({test_pct:.2f}%)')

distinct_files_with_loops_df = for_loops_csv['file'].unique()
total_distinct_files_with_loops = len(distinct_files_with_loops_df)
test_total_distinct_files_with_loops = len(loops_in_tests_df['file'].unique())
distinct_test_pct = (test_total_distinct_files_with_loops / float(total_distinct_files_with_loops)) * 100

print()
print(f'    distinct files with loops: {total_distinct_files_with_loops:,}')
print(f'    distinct test files with loops: {test_total_distinct_files_with_loops:,} ({distinct_test_pct:.2f})%')

for i in range(1, len(patterns)):
    pattern_over_total_loops(patterns[i], total_loops,
                             total_distinct_files_with_loops)


csv_pattern2 = pd.read_csv(csv_path(patterns[1]))
csv_pattern3 = pd.read_csv(csv_path(patterns[2]))
csv_pattern4 = pd.read_csv(csv_path(patterns[3]))
csv_pattern5 = pd.read_csv(csv_path(patterns[4]))
csv_pattern6 = pd.read_csv(csv_path(patterns[5]))

print_intersection(superset_csv=csv_pattern2, subset_csv=csv_pattern3, msg=f'{patterns[2]} is a subset of {patterns[1]}')
print_intersection(superset_csv=csv_pattern4, subset_csv=csv_pattern5, msg=f'{patterns[3]} is a subset of {patterns[2]}')
print_intersection(superset_csv=csv_pattern4, subset_csv=csv_pattern6, msg=f'{patterns[4]} is a subset of {patterns[2]}')
