from dataclasses import dataclass

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

    def strict_within(self, other: 'Range') -> bool:
        return self.starts_just_after(other) and self.ends_just_before(other)

    def start_row_eq(self, row: int) -> bool:
        return self.s_point.row == row

    def start_row(self) -> int:
        return self.s_point.row

    def after_n_lines(self, other: 'Range', n_lines: int) -> bool:
        return self.s_point.row == other.s_point.row + n_lines

    def starts_just_after(self, other: 'Range') -> bool:
        return self.after_n_lines(other, 1)

    def ends_just_before(self, other: 'Range') -> bool:
        return self.e_point.row == other.e_point.row - 1
