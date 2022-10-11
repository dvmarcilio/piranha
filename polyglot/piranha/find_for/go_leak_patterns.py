from dataclasses import dataclass
import datetime
import os
import subprocess
from polyglot_piranha import run_piranha_cli
import csv
import argparse
from dataclass_csv import DataclassReader
from analysis_dataclasses import CsvRow, Range, Point


@dataclass(eq=True, frozen=True)
class FuncLiteral:
    range: Range
    send_stmts: 'list[Range]'


@dataclass(eq=True, frozen=True)
class Channel:
    id: str
    range: Range


@dataclass(eq=True, frozen=True)
class MethodDecl:
    file: str
    range: Range
    channels: 'list[Channel]'
    func_literals: 'list[FuncLiteral]'
    after_return_stmt: 'Range'
    # after_channel_receive: 'Range'

    def chan_names(self):
        return [ c.id for c in self.channels ]

def range_from_match_range(match_range) -> Range:
    s_p = Point(match_range.start_point.row, match_range.start_point.column)
    e_p = Point(match_range.end_point.row, match_range.end_point.column)
    return Range(s_p, e_p)


def ranges_dict(summary_matches) -> 'tuple[dict[str, list[Range]], list[Channel]]':
    r_d = {}
    chans: 'list[Channel]' = []
    for match in summary_matches:
        rule_name = match[0]
        match_range: Range = range_from_match_range(match[1].range)
        if rule_name == 'make_chan':
            chan_matches: 'dict[str, str]' = match[1].matches
            chans.append(Channel(chan_matches['chan_id'], match_range))
        elif rule_name in r_d:
            r_d[rule_name].append(match_range)
        else:
            r_d[rule_name] = [match_range]

    for rule, ranges in r_d.items():
        r_d[rule] = list(reversed(ranges))

    chans = list(reversed(chans))

    return r_d, chans


def run_for_piranha_summary(piranha_summary) -> 'list[MethodDecl]':
    m_decls: 'list[MethodDecl]' = []
    for summary in piranha_summary:
        file_path: str = summary.path
        results = ranges_dict(summary.matches)
        ranges_by_rule: 'dict[str, list[Range]]' = results[0]
        chans: 'list[Channel]' = results[1]

        if all([rule_name in ranges_by_rule for rule_name in mandatory_rule_names]):
            for m_decl_range in ranges_by_rule['method_decl']:
                func_literals: 'list[FuncLiteral]' = []
                after_send_stmt_ranges: 'list[Range]' = []

                for func_lit_range in ranges_by_rule['func_lit']:
                    # ordered by line, don't need to look ones that are after
                    if func_lit_range.after(m_decl_range):
                        break

                    if func_lit_range.within(m_decl_range):
                        within_send_stmts: 'list[Range]' = []
                        for send_stmt_range in ranges_by_rule['send_stmt']:
                            if send_stmt_range.after(func_lit_range):
                                break

                            if send_stmt_range.within(func_lit_range):
                                within_send_stmts.append(send_stmt_range)
                                func_literals.append(
                                    FuncLiteral(func_lit_range,
                                                within_send_stmts)
                                )
                            elif send_stmt_range.after(func_lit_range):
                                after_send_stmt_ranges.append(send_stmt_range)

                if len(func_literals) > 0:
                    # method_declaration
                    # # func_literal
                    # # # send_statement
                    return_after_func_lits: 'Range|None' = None
                    for ret_range in ranges_by_rule['return_stmt']:
                        if ret_range.after(m_decl_range):
                            break

                        if ret_range.within(m_decl_range) and \
                                all(ret_range.after(func_lit.range) for func_lit in func_literals):
                            # return after all func_literals
                            return_after_func_lits = ret_range
                            break

                    # channels before func_literal
                    chans_before_func_lits: 'list[Channel]' = []
                    if len(chans) > 0:
                        for chan in chans:
                            if chan.range.after(m_decl_range):
                                break

                            if chan.range.within(m_decl_range) and \
                                    all(chan.range.before(func_lit.range) for func_lit in func_literals):
                                chans_before_func_lits.append(chan)

                    # method_declaration
                    # # func_literal
                    # # # send_statement
                    # # return_statement
                    if return_after_func_lits:
                        # for send_stmt_range in after_send_stmt_ranges:
                        #     # method_declaration
                        #     # # func_literal
                        #     # # # send_statement
                        #     # # return_statement
                        #     # # send_statement
                        #     if send_stmt_range.after(return_after_func_lits):
                        #         m_d = MethodDecl(
                        #             file_path, m_decl_range, chans_before_func_lits, func_literals, return_after_func_lits, send_stmt_range)
                        #         m_decls.append(m_d)
                        #         print(m_d)
                        #         break

                        m_d = MethodDecl(
                            file_path, m_decl_range, chans_before_func_lits, func_literals, return_after_func_lits)
                        m_decls.append(m_d)
                        print(m_d)
                        break

    return m_decls


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
revision_file_path = base_output_path + 'revision.txt'
with open(revision_file_path, 'w+') as f:
    rev = subprocess.check_output(cwd=os.path.dirname(codebase_path),
                                  args=['git', 'rev-parse',
                                        'HEAD']).decode('ascii').strip()
    f.write(rev)

config_path = os.path.join(base_path, 'configurations_go_leak/')

mandatory_rule_names = [
    'send_stmt',
    'func_lit',
    'method_decl',
    'return_stmt',
]

m_decls: 'list[MethodDecl]' = []

# ideally a root dir with several projects (dirs) as 1st level
if os.path.isdir(codebase_path):
    sub_dirs = next(os.walk(codebase_path))[1]
    for curr_dir in sub_dirs:
        dir_path = os.path.join(codebase_path, curr_dir)
        # print(f'Running for {dir_path}')
        piranha_summary = run_piranha_cli(
            dir_path, config_path, should_rewrite_files=False)
        m_decls.extend(run_for_piranha_summary(piranha_summary))
else:
    piranha_summary = run_piranha_cli(
        codebase_path, config_path, should_rewrite_files=False)
    m_decls.extend(run_for_piranha_summary(piranha_summary))

for m in m_decls:
    print(f'\n{m}')
