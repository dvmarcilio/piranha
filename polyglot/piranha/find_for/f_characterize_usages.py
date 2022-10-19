import os
import json
import glob
import argparse
import sys
from polyglot_piranha import run_piranha_cli

from f_dataclasses import EnhancedJSONEncoder, Pattern, Match, PatternMatch, Point, Range, dataclass_from_dict


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


def paths_in_txt(path: str) -> 'list[str]':
    paths: 'list[str]' = []
    with open(base_path + '/' + path, 'r') as f:
        paths = [p.rstrip() for p in f]
    return paths


def summary_for_file(file: str, config_path: str):
    return run_piranha_cli(
        file, config_path, should_rewrite_files=False)


def compute_pattern_for_identifier(bool_id: str, bool_id_range: Range, mdecl_range: Range, matches_by_rule: 'dict[str, list[Match]]', file_path: str, matches_queue: 'list[PatternMatch]' = []) -> 'list[PatternMatch]':
    pattern_matches: 'list[PatternMatch]' = []

    for return_rule in return_rules:
        for return_id_match in matches_by_rule.get(return_rule, []):
            if return_id_match.range.before(bool_id_range):
                continue
            if return_id_match.range.after(mdecl_range):
                break

            if return_id_match.range.within(mdecl_range):
                if bool_id == return_id_match.matches_dict['ret_id']:
                    pattern_match = PatternMatch(
                        'return_variable', file_path, return_id_match)
                    pattern_matches.append(pattern_match)

    # TODO alias analysis for the identifier?

    for if_condition_match in matches_by_rule.get('if_condition', []):
        if if_condition_match.range.before(bool_id_range):
            continue
        if if_condition_match.range.after(mdecl_range):
            break

        if if_condition_match.range.within(mdecl_range):
            temp_condition_file_path = bool_id + '_condition.go'
            with open(temp_condition_file_path, "w") as f:
                f.write(if_condition_match.matches_dict['if_cond'] + '\n')

            piranha_summary = summary_for_file(
                temp_condition_file_path, ids_config_path)
            for summary in piranha_summary:
                found = False
                m_b_r: 'dict[str, list[Match]]' = matches_dict(summary.matches)
                for id_match in m_b_r.get('identifier', []):
                    if bool_id == id_match.matches_dict['id']:
                        found = True
                        if_match = PatternMatch(
                            'if_condition', file_path, if_condition_match)
                        patch_match = PatternMatch(
                            'if_condition_variable', file_path, id_match)
                        pattern_matches.extend([if_match, patch_match])
                        break

                if found:
                    break

            os.remove(temp_condition_file_path)

    return pattern_matches


def write_json(patterns: 'list[Pattern]', json_index):
    if len(patterns) > 0:
        with open(base_output_path + f'{json_index}.json', 'w') as f:
            f.write(json.dumps(patterns, cls=EnhancedJSONEncoder, indent=4))
        json_index += 1


paths: 'list[str]' = []

parser = argparse.ArgumentParser()
parser.add_argument('--test_paths', action='store_true', default=False)
args = parser.parse_args()

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
base_path = os.path.join(base_path, 'f-calls-checker/')
original_matches_path = os.path.join(base_path, 'matches/non-tests/')
base_output_path = os.path.join(base_path, 'matches-usage/')

general_config_path = os.path.join(
    base_path, 'configurations-usage', 'general/')
ids_config_path = os.path.join(
    base_path, 'configurations-usage', 'identifier/')

if args.test_paths:
    paths = paths_in_txt(
        'paths_test.txt') + paths_in_txt('paths_test_no_import.txt')
    base_output_path += 'tests/'
    print('Running for test Paths')
else:
    print('*Not* running for test paths')
    base_output_path += 'non-tests/'
    paths = paths_in_txt(
        'paths.txt') + paths_in_txt('paths_no_import.txt')

os.makedirs(base_output_path, exist_ok=True)

return_rules = ['return_id', 'return_id_id', 'return_id_nil', ]

json_index = 0

# we need to create temp files as py piranha_cli takes file paths and checks for file extension

# for identifiers in an if condition
# capture the whole condition, then re-parse and match all identifiers
# probably gonna have several summaries: map collect the matches
for json_file_path in glob.glob(original_matches_path + '/*.json'):
    patterns: 'list[Pattern]' = []

    with open(json_file_path) as file:
        patterns_dict = json.load(file)
        for p in patterns_dict:
            pattern: Pattern = dataclass_from_dict(Pattern, p)
            piranha_summary = summary_for_file(
                pattern.file, general_config_path)
            for summary in piranha_summary:
                matches_by_rule: 'dict[str, list[Match]]' = matches_dict(
                    summary.matches)

                for return_call_match in matches_by_rule.get('return_call', []):
                    name = 'return_call;' + pattern.name
                    p_match = PatternMatch(
                        'return_call', pattern.file, return_call_match)
                    pattern_matches = [dataclass_from_dict(PatternMatch, m) for m in pattern.matches]
                    matches = [p_match] + pattern_matches
                    usage_p = Pattern(name, pattern.file, matches)
                    patterns.append(usage_p)

                for assignment_call_match in matches_by_rule.get('assignment_call', []):
                    mdecl_match = parent_mdecl_func_match(
                        matches_by_rule, assignment_call_match)
                    if mdecl_match:
                        bool_id = assignment_call_match.matches_dict['bool_id']
                        matches: 'list[PatternMatch]' = compute_pattern_for_identifier(
                            bool_id, assignment_call_match.
                            range, mdecl_match.range, matches_by_rule, pattern.file)

                        p_match = PatternMatch(
                            'assignment_call', pattern.file, assignment_call_match)
                        pattern_matches = [dataclass_from_dict(PatternMatch, m) for m in pattern.matches]
                        final_matches: 'list[PatternMatch]' = [
                            p_match] + matches + pattern_matches
                        pattern_name = PatternMatch.p_name_from_lst(
                            final_matches)
                        usage_p = Pattern(
                            pattern_name, pattern.file, final_matches)
                        patterns.append(usage_p)

            if len(patterns) == 0:
                patterns = [
                    Pattern('no_usage_pattern;' + pattern.name, pattern.file, pattern.matches)]

    write_json(patterns, json_index)
    json_index += 1
