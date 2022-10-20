from dataclasses import dataclass
import dataclasses

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

    def after(self, other: 'Range') -> bool:
        """
        Assumes that each Range will be in different lines.
        Returns:
          start_point.row > other.start_point.row and \
            end_point.row > other.end_point.row
        """
        return self.s_point.row > other.s_point.row and \
            self.e_point.row > other.e_point.row

    def before(self, other: 'Range') -> bool:
        """
        Assumes that each Range will be in different lines.
        Returns:
          start_point.row < other.start_point.row and \
            end_point.row < other.end_point.row
        """
        return self.s_point.row < other.s_point.row and \
            self.e_point.row < other.e_point.row

    def strict_within(self, other: 'Range') -> bool:
        return self.starts_just_after(other) and self.ends_just_before(other)

    def start_row_eq(self, row: int) -> bool:
        return self.s_point.row == row

    def start_row(self) -> int:
        return self.s_point.row

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
class FuncLiteral:
    range: Range
    send_stmts: 'list[Range]'
    if_stmts: 'list[Range]'
    select_stmts: 'list[Range]'
    is_pattern2: bool

    def start_line(self) -> int:
        return self.range.start_row() + 1

@dataclass(eq=True, frozen=True)
class Channel:
    id: str
    range: Range

    def start_line(self) -> int:
        return self.range.start_row() + 1

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
    channels: 'list[Channel]'
    func_literals: 'list[FuncLiteral]'
    return_stmt_after: 'list[Range]'
    channel_receive_after: 'list[Range]'

    def chan_names(self) -> 'list[str]':
        return [c.id for c in self.channels]

    def is_pattern2(self) -> bool:
        return any(fl.is_pattern2 for fl in self.func_literals)

    def start_line(self) -> int:
        return self.range.start_row() + 1

@dataclass(eq=True, frozen=True)
class Pattern:
    name: str
    m_decl: MethodDecl

def dataclass_from_dict(klass, d):
    try:
        fieldtypes = {f.name:f.type for f in dataclasses.fields(klass)}
        return klass(**{f:dataclass_from_dict(fieldtypes[f],d[f]) for f in d})
    except:
        return d # Not a dataclass field
