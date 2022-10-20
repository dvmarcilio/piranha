import dataclasses
import datetime
import glob
import json
import os
import subprocess
from polyglot_piranha import run_piranha_cli
import argparse

from analysis_dataclasses import Point, Range, Channel, FuncLiteral, Pattern, MethodDecl


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


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
        if rule_name == 'chan_make':
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


def run_for_piranha_summary(piranha_summary) -> 'list[Pattern]':
    patterns: 'list[Pattern]' = []
    for summary in piranha_summary:
        file_path: str = summary.path
        results = ranges_dict(summary.matches)
        ranges_by_rule: 'dict[str, list[Range]]' = results[0]
        chans: 'list[Channel]' = results[1]
        all_func_lits_ranges: 'list[Range]' = []
        send_channel_ids: 'set[str]' = set()

        if all([rule_name in ranges_by_rule for rule_name in mandatory_rule_names]):
            for m_decl_range in ranges_by_rule['method_decl']:
                func_literals: 'list[FuncLiteral]' = []

                for func_lit_range in ranges_by_rule['func_lit']:
                    # ordered by line, don't need to look ones that are after
                    if func_lit_range.after(m_decl_range):
                        break

                    if func_lit_range.within(m_decl_range):
                        all_func_lits_ranges.append(func_lit_range)
                        within_send_stmts: 'list[Range]' = []
                        for send_stmt_range in ranges_by_rule['send_stmt']:
                            if send_stmt_range.after(func_lit_range):
                                break
                            if send_stmt_range.within(func_lit_range):

                                within_send_stmts.append(send_stmt_range)

                        # within_send is required
                        if len(within_send_stmts) > 0:
                            within_if_stmts: 'list[Range]' = []
                            within_select_stmts: 'list[Range]' = []
                            for if_stmt_range in ranges_by_rule.get('if_stmt', []):
                                if if_stmt_range.after(func_lit_range):
                                    break
                                if if_stmt_range.within(func_lit_range):
                                    within_if_stmts.append(if_stmt_range)

                            for select_stmt_range in ranges_by_rule.get('select_stmt', []):
                                if select_stmt_range.after(func_lit_range):
                                    break
                                if select_stmt_range.within(func_lit_range):
                                    within_select_stmts.append(
                                        select_stmt_range)

                            if_select_stmts = within_if_stmts + within_select_stmts

                            is_pattern2 = False
                            for send_statement in within_send_stmts:
                                is_pattern1 = any(send_statement.within(
                                    if_select) for if_select in if_select_stmts)
                                if not is_pattern1:
                                    is_pattern2 = True
                                    break

                            func_literals.append(FuncLiteral(
                                func_lit_range, within_send_stmts, within_if_stmts, within_select_stmts, is_pattern2))

                if len(func_literals) > 0:
                    # method_declaration
                    # # func_literal
                    # # # send_statement
                    returns_after_func_lits: 'list[Range]' = []
                    for ret_range in ranges_by_rule['return_stmt']:
                        if ret_range.after(m_decl_range):
                            break

                        if ret_range.within(m_decl_range) and \
                                all(not ret_range.within(func_lit_range) for func_lit_range in all_func_lits_ranges) and \
                                any(ret_range.after(func_lit_range) for func_lit_range in all_func_lits_ranges):
                            # return not inside any func_literal
                            returns_after_func_lits.append(ret_range)

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
                    if len(returns_after_func_lits) > 0:

                        chan_receives_after_rets: 'list[Range]' = []
                        for chan_rec in ranges_by_rule['chan_receive']:
                            if chan_rec.after(m_decl_range):
                                break

                            if chan_rec.within(m_decl_range) and \
                                    any(chan_rec.after(ret_range) for ret_range in returns_after_func_lits):
                                chan_receives_after_rets.append(chan_rec)

                        # method_declaration
                        # # func_literal
                        # # # send_statement
                        # # return_statement
                        # # <-ch
                        if len(chan_receives_after_rets) > 0:

                            def after_func_lit_within_mdecl(ranges_to_check: 'list[Range]') -> 'list[Range]':
                                func_lit_ranges: 'list[Range]' = [
                                    func_lit.range for func_lit in func_literals]
                                ranges: 'list[Range]' = []
                                for func_lit_range in func_lit_ranges:
                                    for if_slct_range in ranges_to_check:
                                        if if_slct_range.after(m_decl_range):
                                            break

                                        if if_slct_range.after(func_lit_range) and \
                                                if_slct_range.within(m_decl_range):
                                            ranges.append(
                                                if_slct_range)

                                return ranges

                            after_if_ranges: 'list[Range]' = after_func_lit_within_mdecl(ranges_by_rule.get(
                                'if_stmt', []))
                            after_select_ranges: 'list[Range]' = after_func_lit_within_mdecl(ranges_by_rule.get(
                                'select_stmt', []))
                            if_select_stmt_ranges: 'list[Range]' = after_if_ranges + \
                                after_select_ranges

                            has_any_receive_inside_if_slct = False
                            for if_slct_range in if_select_stmt_ranges:
                                if any(chan_receive.within(if_slct_range) for chan_receive in chan_receives_after_rets):
                                    has_any_receive_inside_if_slct = True
                                    break

                            if not has_any_receive_inside_if_slct:

                                m_d = MethodDecl(
                                    file_path, m_decl_range, chans_before_func_lits, func_literals, returns_after_func_lits, chan_receives_after_rets)

                                pattern_name: str = ''
                                if chans_before_func_lits:
                                    pattern_name = 'advanced2' if m_d.is_pattern2() else 'advanced1'
                                else:
                                    pattern_name = 'basic'

                                patterns.append(Pattern(pattern_name, m_d))

    return patterns


parser = argparse.ArgumentParser()
parser.add_argument('codebase_path', type=str)
parser.add_argument('output_path', type=str, nargs="?")
parser.add_argument('--skip-threshold-mb',
                    dest='skip_threshold_mb', type=int, default=1)
args = parser.parse_args()

base_path = os.path.join(os.path.dirname(__file__))
codebase_path = os.path.normpath(os.path.abspath(args.codebase_path)) + os.path.sep

base_output_path = ''
if not args.output_path:
    time_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base_output_path = os.path.join(base_path, 'output_' + time_str + '/')
else:
    base_output_path = os.path.abspath(args.output_path) + '/'

if not os.path.exists(base_output_path):
    os.mkdir(base_output_path)

matches_path = base_output_path + 'matches/'
os.mkdir(matches_path)

print('codebase path:', codebase_path, flush=True)
print('base output path:', base_output_path, flush=True)
print('matches path:', matches_path, flush=True)

revision_file_path = base_output_path + 'revision.txt'
with open(revision_file_path, 'w+') as f:
    rev = subprocess.check_output(cwd=os.path.dirname(codebase_path),
                                  args=['git', 'rev-parse',
                                        'HEAD']).decode('ascii').strip()
    print('git rev-parse HEAD:', rev)
    f.write(rev)

config_path = os.path.join(base_path, 'configurations_go_leak/')

mandatory_rule_names = [
    'send_stmt',
    'func_lit',
    'method_decl',
    'return_stmt',
    'chan_receive'
]

json_index = 0


def write_json(patterns: 'list[Pattern]'):
    global json_index
    if len(patterns) > 0:
        with open(matches_path + f'{json_index}.json', 'w') as f:
            f.write(json.dumps(patterns, cls=EnhancedJSONEncoder, indent=4))
        print_with_timestamp(f'Found match #{json_index}')
        json_index += 1


def do_run_write_for_file(file: str):
    summary = run_piranha_cli(
        file, config_path, should_rewrite_files=False)
    curr_patterns = run_for_piranha_summary(summary)
    write_json(curr_patterns)


def write_to_file(txt: str, file_path):
    with open(file_path, 'a+') as f:
        f.write(txt + '\n')


def print_with_timestamp(msg):
    now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    print('[' + now + '] ' + msg, flush=True)


executed_file = base_output_path + 'executed.txt'
skipped_file = base_output_path + 'skipped.txt'

count = 1
if os.path.isdir(codebase_path):
    # file by file
    for go_file in glob.glob(codebase_path + '/**/*.go', recursive=True):
        file_size_mb = os.path.getsize(go_file) / 1e+6
        if go_file.endswith('-gen.go'):
            # print_with_timestamp(f"Skipping generated file '{go_file}'")
            write_to_file(go_file, skipped_file)
            continue
        if file_size_mb > args.skip_threshold_mb:
            # print_with_timestamp(f"Skipping large file '{go_file}'")
            write_to_file(go_file, skipped_file)
            continue

        write_to_file(go_file, executed_file)
        do_run_write_for_file(go_file)
        count += 1
        if count % 500 == 0:
            print_with_timestamp(f'Executed for {count} files')

else:
    do_run_write_for_file(codebase_path)
