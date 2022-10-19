from dataclasses import dataclass
import dataclasses
import json


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


@dataclass(eq=True, frozen=True)
class Point:
    row: int
    col: int


@dataclass(eq=True, frozen=True)
class Range:
    s_point: Point
    e_point: Point

    def within(self, other_range: 'Range') -> bool:
        return (
            self.s_point.row >= other_range.s_point.row
            and self.e_point.row <= other_range.e_point.row
        )

    def after(self, other: 'Range') -> bool:
        """
        Assumes that each Range will be in different lines.
        Returns:
          start_point.row > other.start_point.row and \
            end_point.row > other.end_point.row
        """
        return (
            self.s_point.row > other.s_point.row
            and self.e_point.row > other.e_point.row
        )

    def before(self, other: 'Range') -> bool:
        """
        Assumes that each Range will be in different lines.
        Returns:
          start_point.row < other.start_point.row and \
            end_point.row < other.end_point.row
        """
        return (
            self.s_point.row < other.s_point.row
            and self.e_point.row < other.e_point.row
        )

    def strict_within(self, other: 'Range') -> bool:
        return self.starts_just_after(other) and self.ends_just_before(other)

    def start_row_eq(self, row: int) -> bool:
        return self.s_point.row == row

    def end_row_eq(self, row: int) -> bool:
        return self.e_point.row == row

    def eq_start_or_end_row(self, other: 'Range') -> bool:
        return self.eq_start_row(other) or self.eq_end_row(other)

    def eq_start_row(self, other: 'Range') -> bool:
        return self.start_row() == other.start_row()

    def eq_end_row(self, other: 'Range') -> bool:
        return self.end_row() == other.end_row()

    def start_row(self) -> int:
        return self.s_point.row

    def end_row(self) -> int:
        return self.e_point.row

    def start_line(self) -> int:
        return self.start_row() + 1

    def after_n_lines(self, other: 'Range', n_lines: int) -> bool:
        return self.s_point.row == other.s_point.row + n_lines

    def starts_just_after(self, other: 'Range') -> bool:
        return self.after_n_lines(other, 1)

    def ends_just_before(self, other: 'Range') -> bool:
        return self.e_point.row == other.e_point.row - 1

    @classmethod
    def empty(cls) -> 'Range':
        return Range(Point(-1, -1), Point(-1, -1))


@dataclass(eq=True, frozen=True)
class Match:
    range: Range
    matches_dict: 'dict[str, str]'

    @classmethod
    def empty(cls) -> 'Match':
        return Match(Range.empty(), {})


@dataclass(eq=True, frozen=True)
class MethodDecl:
    file: str
    range: Range

    def start_line(self) -> int:
        return self.range.start_row() + 1


@dataclass(eq=True, frozen=True)
class Pattern:
    name: str
    file: str
    matches: 'list[PatternMatch]'


@dataclass(eq=True, frozen=True)
class PatternMatch:
    name: str
    file: str
    match: Match

    @classmethod
    def p_name_from_lst(cls, lst: 'list[PatternMatch]') -> str:
        return ";".join([pm.name for pm in lst])

def dataclass_from_dict(klass, d):
    try:
        fieldtypes = {f.name: f.type for f in dataclasses.fields(klass)}
        return klass(**{f: dataclass_from_dict(fieldtypes[f], d[f]) for f in d})
    except:
        return d  # Not a dataclass field
