from dataclasses import dataclass
import datetime
import os
import subprocess
from polyglot_piranha import run_piranha_cli
import csv
import argparse
from dataclass_csv import DataclassReader

# python3 -m pip install dataclass_csv

@dataclass(eq=True, frozen=True)
class CsvRow:
    """
    Defined to allow a csv row to be hashable; so it can be used in set's and map's.
    """
    file: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    rule_name: str

    @classmethod
    def from_range(cls, file: str, rule_name: str, r: 'Range') -> 'CsvRow':
        return CsvRow(
            file=file, rule_name=rule_name,
            start_row=r.s_point.row, start_col=r.s_point.col,
            end_row=r.e_point.row, end_col=r.e_point.col,
        )

    def raw_csv_row(self):
        return [
            self.file,
            self.start_row, self.start_col,
            self.end_row, self.end_col,
            self.rule_name,
        ]
@dataclass(eq=True, frozen=True)
class Point:
    row: int
    col: int

@dataclass(eq=True, frozen=True)
class Range:
    s_point: Point
    e_point: Point

    def within(self, other_range: 'Range') -> bool:
        """
        Assumes that each Range will be in different lines.
        """
        return self.s_point.row > other_range.s_point.row and \
            self.e_point.row < other_range.e_point.row

    def after(self, other_range: 'Range') -> bool:
        """
        Assumes that each Range will be in different lines.
        """
        return self.s_point.row > other_range.s_point.row and \
            self.e_point.row > other_range.e_point.row

    def strict_within(self, other_range: 'Range') -> bool:
        """

        """
        return self.s_point.row == other_range.s_point.row + 1 and \
            self.e_point.row == other_range.e_point.row - 1

def row_col(point) -> 'tuple[int, int]':
    return point.row, point.column

def distinct_elements_from_list(lst: 'list'):
    # adding to a dict discards duplicates
    # dict maintains insertion order
    return list(dict.fromkeys(lst))

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

def rows_from_csv(csv_path: str) -> 'list[CsvRow]':
    rows: 'list[CsvRow]' = []
    with open(csv_path) as f:
        reader = DataclassReader(f, CsvRow)
        next(reader)  # skip header
        for row in reader:
            rows.append(row)
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

def range_from_match_range(match_range) -> Range:
    s_p = Point(match_range.start_point.row, match_range.start_point.column)
    e_p = Point(match_range.end_point.row, match_range.end_point.column)
    return Range(s_p, e_p)

def summary_ranges_dict(piranha_summary) -> 'dict[str, list[Range]]':
    """
    dict with ranges by unique files
    {
        'file_path': [
            Range(
                s_point = Point(s_row, s_col),
                e_point = Point(e_row, e_col)
            ),
            # ...
        ]
    }
    """
    ranges_dict = {}
    for summary in piranha_summary:
        file_path: str = summary.path
        ranges: 'list[Range]' = []
        for match in summary.matches:
            match_range = match[1].range
            ranges.append(range_from_match_range(match_range))
        ranges_dict[file_path] = ranges

    return ranges_dict

def ranges_dict_from_csv(csv_path)-> 'dict[str, list[Range]]':
    rows: 'list[CsvRow]' = rows_from_csv(csv_path)
    ranges_dict = {}
    for row in rows:
        file = row.file
        row_range = Range(
            Point(row.start_row, row.start_col),
            Point(row.end_row, row.end_col)
        )
        if file in ranges_dict:
            ranges_dict[file].append(row_range)
        else:
            ranges_dict[file] = [row_range]
    return ranges_dict

def run_and_write_for_base_pattern() -> 'dict[str, list[Range]]':
    """
    Runs `find_for` rule for the entire codebase given as argument.
    """
    if os.path.exists(base_output_file_path):
        print("Skipping execution for base rule as csv already exists.",
              flush=True)
        return ranges_dict_from_csv(base_output_file_path)

    print('Executing for base rule', flush=True)
    config_path = os.path.join(base_path, 'configurations/')

    piranha_summary = run_piranha_cli(codebase_path,
                                      config_path,
                                      should_rewrite_files=False)

    write_summaries_to_file(piranha_summary, base_output_file_path)

    return summary_ranges_dict(piranha_summary)

def collect_paths_from_csv(csv_path: str) -> 'set[str]':
    paths: 'list[str]' = []
    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            paths.append(row[0])
    return set(paths)

def go_stmts_and_short_v_decls_ranges(piranha_summary) -> 'tuple[list[Range], list[Range]]':
    go_stmts_ranges: 'list[Range]' = []
    short_var_decls_ranges: 'list[Range]' = []

    for summary in piranha_summary:
        for match in summary.matches:
            rule_name = match[0]
            match_range: Range = range_from_match_range(match[1].range)
            if rule_name == 'short_v_decl':
                short_var_decls_ranges.append(match_range)
            elif rule_name == 'go_stmt':
                go_stmts_ranges.append(match_range)
            else:
                print(f"Rule '{rule_name}' is not what we expected")

    return go_stmts_ranges, short_var_decls_ranges

def append_to_csv(rows: 'list[CsvRow]', csv_path: str):
    should_write_header = not os.path.exists(csv_path)

    with open(csv_path, 'a+') as output_file:
        writer = csv.writer(output_file,
                            delimiter=',',
                            quotechar='"',
                            quoting=csv.QUOTE_NONNUMERIC)

        if should_write_header:
            writer.writerow([
                'file', 'start_row', 'start_col', 'end_row', 'end_col', 'rule_name'
            ])

        for row in rows:
            writer.writerow(row.raw_csv_row())


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

for_ranges_dict: 'dict[str, list[Range]]' = run_and_write_for_base_pattern()

within_csv = base_output_path + '2_any_go_stmt.csv'
strict_within_csv = base_output_path + '3_only.csv'

# could be more effective if we ran piranha only on the for_stmt lines
## extract the whole for_stmt
## store temp file with it
## recalculate the line number
for file_path, for_ranges_list in for_ranges_dict.items():
    config_path = os.path.join(base_path, 'v2/')

    piranha_summary = run_piranha_cli(file_path,
                                      config_path,
                                      should_rewrite_files=False)

    ranges = go_stmts_and_short_v_decls_ranges(piranha_summary)
    go_stmts_ranges: 'list[Range]' = ranges[0]
    short_var_decls_ranges: 'list[Range]' = ranges[1]

    # go stmts inside for loop

    # on the general case, the lengths of
    ## short_var_decls should be way higher than for loops
    ## for loops should be higher than go_stmts

    # ranges are returned in reversed order
    within = []
    strict_within = []

    for for_range in reversed(for_ranges_list):

        for go_range in reversed(go_stmts_ranges):
            if go_range.after(for_range):
                # avoid looking into others: ranges are ordered
                break

            if go_range.strict_within(for_range):
                strict_within.append(CsvRow.from_range(file_path, 'only_go_stmt', go_range))
            elif go_range.within(for_range):
                within.append(CsvRow.from_range(file_path, 'any_go_stmt_in_for', go_range))

    append_to_csv(within, within_csv)
    append_to_csv(strict_within, strict_within_csv)
