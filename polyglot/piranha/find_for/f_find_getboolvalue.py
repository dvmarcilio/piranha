import argparse
from dataclasses import dataclass
import glob
import json
import os
import sys
from polyglot_piranha import run_piranha_cli

from f_dataclasses import Point, Range, Pattern, PatternMatch, EnhancedJSONEncoder, Match


def range_from_match_range(match_range) -> Range:
    s_p = Point(match_range.start_point.row, match_range.start_point.column)
    e_p = Point(match_range.end_point.row, match_range.end_point.column)
    return Range(s_p, e_p)


def matches_dict(summary_matches) -> 'dict[str, list[Match]]':
    r_d = {}
    for match in summary_matches:
        rule_name = match[0]
        match_range: Range = range_from_match_range(match[1].range)
        matches_dict = match[1].matches
        match = Match(match_range, matches_dict)
        if rule_name in r_d:
            r_d[rule_name].append(match)
        else:
            r_d[rule_name] = [match]

    for rule, ranges in r_d.items():
        r_d[rule] = list(reversed(ranges))

    return r_d


def write_to_file(txt: str, file_path):
    with open(file_path, 'a+') as f:
        f.write(txt + '\n')


def summary_for_file(file: str, config_path: str):
    return run_piranha_cli(
        file, config_path, should_rewrite_files=False)


def do_run_write_for_file(file: str):
    summary = summary_for_file(file, config_path)
    curr_patterns = run_for_piranha_summary(summary)
    if len(curr_patterns) == 0:
        curr_patterns = [Pattern('no_piranha_summary', file, [])]
    write_json(curr_patterns)


def write_json(patterns: 'list[Pattern]'):
    global json_index
    if len(patterns) > 0:
        with open(base_output_path + f'{json_index}.json', 'w') as f:
            f.write(json.dumps(patterns, cls=EnhancedJSONEncoder, indent=4))
        json_index += 1


def parent_mdecl_func_match(matches_by_rule: 'dict[str, list[Match]]', within_match: Match) -> 'Match|None':
    """
    Returns the range of the Method or Function that contains `within`
    """
    within_range = within_match.range
    for mdecl_match in matches_by_rule.get('method_decl', []):
        if mdecl_match.range.after(within_range):
            break

        if within_range.within(mdecl_match.range):
            return mdecl_match

    for func_match in matches_by_rule.get('function_decl', []):
        if func_match.range.after(within_range):
            break

        if within_range.within(func_match.range):
            return func_match

    return None


def lookup_in_other_file(id: str, root_dir: str) -> 'PatternMatch|None':
    # looks for the constant/var definition in every .go file in the directory
    for go_file_path in glob.glob(root_dir + '/*.go'):
        piranha_summary = summary_for_file(
            go_file_path, config_path)

        for summary in piranha_summary:
            matches_by_rule: 'dict[str, list[Match]]' = matches_dict(
                summary.matches)
            # duplicated from below
            for const_str_literal_match in matches_by_rule.get('const_str_literal', []):
                const_id = const_str_literal_match.matches_dict['const_id']
                if const_id == id:
                    return PatternMatch('lookup_const_str_literal', go_file_path, const_str_literal_match)

            for var_str_literal_match in matches_by_rule.get('var_str_literal', []):
                var_id = var_str_literal_match.matches_dict['var_id']
                if var_id == id:
                    return PatternMatch('lookup_var_str_literal', go_file_path, var_str_literal_match)

    return None


def compute_pattern_for_selector_exp(selector_exp: str, import_decl_matches: 'list[Match]') -> 'PatternMatch|None':
    # XXX ideally, we should parse and not deal with str?
    assert (len(import_decl_matches) == 1)
    import_decl = import_decl_matches[0].matches_dict.get('import_decl', '')

    # FIXME will break in the case of multiple `.`
    split = selector_exp.split('.')
    package = split[0]
    id = split[1]
    named_import_prefix = f'{package} '

    for line in import_decl.splitlines():
        line = line.strip()
        if line.startswith(f'"{args.local_import_prefix}') and line.endswith(f'/{package}"'):
            # strip surrounding `"`
            dir_path = args.source_path + line[1:-1]

            const_lookup_match = lookup_in_other_file(id, dir_path)
            if const_lookup_match:
                # TODO add the import to the matches dict?
                return const_lookup_match
        elif line.startswith(named_import_prefix):
            # with surrounding `"`
            dir_path = line[len(named_import_prefix):]
            # strip surrounding `"`
            dir_path = args.source_path + dir_path[1:-1]

            const_lookup_match = lookup_in_other_file(id, dir_path)
            if const_lookup_match:
                return const_lookup_match

    return None


def compute_pattern_for_identifier(identifier: str, mdecl_range: Range, matches_by_rule: 'dict[str, list[Match]]', file_path: str, matches_queue: 'list[PatternMatch]' = []) -> 'list[PatternMatch]':
    """
    `identifier` cannot be a constant in another file, since it would be a `selector_expression`.
    """
    # Inefficient as usual, but should get the job done
    # TODO: efficiency: populate a map for already computed within X m_decl

    no_pattern = PatternMatch(
        'no_pattern_identifier', file_path, Match.empty())

    for s_vdecl_match in matches_by_rule.get('short_var_decl_val_str_literal', []):
        if s_vdecl_match.range.after(mdecl_range):
            break

        if s_vdecl_match.range.within(mdecl_range):
            if identifier == s_vdecl_match.matches_dict['s_vdecl_id']:
                pattern_match = PatternMatch(
                    'short_var_decl_str_literal', file_path, s_vdecl_match)
                return matches_queue + [pattern_match]

    # TODO: const value for another identifier?
    # TODO: const value for another const in another file?

    for s_vdecl_match in matches_by_rule.get('short_var_decl_val_selector_exp', []):
        if s_vdecl_match.range.after(mdecl_range):
            break

        if s_vdecl_match.range.within(mdecl_range):
            if identifier == s_vdecl_match.matches_dict['s_vdecl_id']:
                selector_exp = s_vdecl_match.matches_dict['s_vdecl_val_selector_exp']
                import_decl = matches_by_rule.get('import_decl', [])
                const_import_match = PatternMatch(
                    'short_var_decl_selector_exp', file_path, s_vdecl_match)
                const_pattern_match = compute_pattern_for_selector_exp(
                    selector_exp, import_decl)
                if const_pattern_match:
                    pattern_matches = [const_import_match, const_pattern_match]
                    return matches_queue + pattern_matches
                else:
                    return matches_queue + [const_import_match, no_pattern]

    for const_str_literal_match in matches_by_rule.get('const_str_literal', []):
        const_id = const_str_literal_match.matches_dict['const_id']
        if const_id == identifier:
            pattern_match = PatternMatch(
                'const_str_literal', file_path, const_str_literal_match)
            return matches_queue + [pattern_match]

    for var_str_literal_match in matches_by_rule.get('var_str_literal', []):
        var_id = var_str_literal_match.matches_dict['var_id']
        if var_id == identifier:
            pattern_match = PatternMatch(
                'var_str_literal', file_path, var_str_literal_match)
            return matches_queue + [pattern_match]

    for str_method_args_match in matches_by_rule.get('str_arguments', []):
        # after() checks both start and end of range
        # args may have a start row after, but it won't have an end row
        if str_method_args_match.range.after(mdecl_range):
            break

        if str_method_args_match.range.within(mdecl_range):
            if identifier == str_method_args_match.matches_dict['param_id']:
                pattern_match = PatternMatch(
                    'str_argument', file_path, str_method_args_match)
                return matches_queue + [pattern_match]

    for s_vdecl_match in matches_by_rule.get('short_var_decl_val_id', []):
        if s_vdecl_match.range.after(mdecl_range):
            break

        if s_vdecl_match.range.within(mdecl_range):
            if identifier == s_vdecl_match.matches_dict['s_vdecl_id']:
                # identifier assigned to another identifier!
                # is it another short val decl in the same method?
                # a const in this file?
                # a const in another file?
                val_arg_id = s_vdecl_match.matches_dict.get(
                    's_vdecl_val_id', '')
                pattern_match = PatternMatch(
                    'short_var_decl_id', file_path, s_vdecl_match)
                matches_queue.append(pattern_match)
                return compute_pattern_for_identifier(val_arg_id, mdecl_range, matches_by_rule, file_path, matches_queue)

    # look into other files in the curr file directory
    # TODO validate that files have the same package?
    # parse `(package_clause (package_identifier) @pckg_id)`
    file_dir = os.path.dirname(file_path)
    lookup_match = lookup_in_other_file(identifier, file_dir)
    if lookup_match:
        return matches_queue + [lookup_match]

    return matches_queue + [no_pattern]


def run_for_piranha_summary(piranha_summary) -> 'list[Pattern]':
    patterns: 'list[Pattern]' = []

    # we may have more than one summary per file
    # rule `str_method_arguments` may match several `string` args
    for summary in piranha_summary:
        file_path: str = summary.path
        matches_by_rule: 'dict[str, list[Match]]' = matches_dict(
            summary.matches)

        len_before = len(patterns)

        for cst in matches_by_rule.get('call_str_literal', []):
            # easiest pattern
            pattern_match = PatternMatch('str_literal', file_path, Match(
                cst.range, {'arg_str_literal': cst.matches_dict['arg_str_literal']}))
            p = Pattern('call_str_literal', file_path, [pattern_match])
            patterns.append(p)

        for cid in matches_by_rule.get('call_identifier', []):
            mdecl_match = parent_mdecl_func_match(matches_by_rule, cid)
            if mdecl_match:
                arg_id = cid.matches_dict.get('arg_id', None)
                if arg_id:
                    pattern_match = PatternMatch(
                        'call_identifier', file_path, Match(cid.range, {'arg_id': arg_id}))
                    pattern_matches = compute_pattern_for_identifier(
                        arg_id, mdecl_match.range, matches_by_rule, file_path, [pattern_match])
                    if pattern_matches:
                        pattern_name = PatternMatch.p_name_from_lst(
                            pattern_matches)
                        p = Pattern(pattern_name, file_path, pattern_matches)
                        patterns.append(p)

        for cse in matches_by_rule.get('call_selector_exp', []):
            arg_selector_exp = cse.matches_dict['arg_selector_exp']
            import_decl = matches_by_rule.get('import_decl', [])
            pattern_match = PatternMatch('call_selector_exp', file_path, Match(
                cse.range, {'const_id': arg_selector_exp}))
            const_pattern_match = compute_pattern_for_selector_exp(
                arg_selector_exp, import_decl)
            if const_pattern_match:
                pattern_matches = [pattern_match, const_pattern_match]
                pattern_name = PatternMatch.p_name_from_lst(
                    pattern_matches)
                p = Pattern(pattern_name, file_path, pattern_matches)
                patterns.append(p)
            else:
                no_pattern = PatternMatch(
                    'no_pattern_selector_exp', file_path, Match.empty())
                pattern_matches = [pattern_match, no_pattern]
                pattern_name = PatternMatch.p_name_from_lst(pattern_matches)
                p = Pattern(pattern_name, file_path, pattern_matches)
                patterns.append(p)

        if len_before == len(patterns):
            p = Pattern('no_pattern', file_path, [])
            patterns.append(p)

    return patterns


parser = argparse.ArgumentParser()
parser.add_argument('--local_import_prefix', type=str)
parser.add_argument('--source_path', type=str)
parser.add_argument('--test_paths', action='store_true', default=False)
args = parser.parse_args()

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
base_path = os.path.join(base_path, 'f-calls-checker/')
base_output_path = os.path.join(base_path, 'matches/')
config_path = os.path.join(base_path, 'configurations/')


def paths_in_txt(path: str) -> 'list[str]':
    paths: 'list[str]' = []
    with open(base_path + '/' + path, 'r') as f:
        paths = [p.rstrip() for p in f]
    return paths


paths: 'list[str]' = []

if args.test_paths:
    paths = paths_in_txt(
        'paths_test.txt') + paths_in_txt('paths_test_no_import.txt')
    base_output_path += 'tests/'
    print('Running for test Paths')
else:
    paths = paths_in_txt(
        'paths.txt') + paths_in_txt('paths_no_import.txt')
    base_output_path += 'non-tests/'
    print('*Not* running for test paths')

os.makedirs(base_output_path, exist_ok=True)

executed_file = base_path + 'executed.txt'
if os.path.exists(executed_file):
    os.remove(executed_file)
json_index = 0

print(f'Running for {len(paths)} files')

for go_file_path in paths:
    write_to_file(go_file_path, executed_file)
    do_run_write_for_file(go_file_path)
