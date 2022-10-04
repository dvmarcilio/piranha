from dataclasses import dataclass

@dataclass
class Point:
    row: int
    column: int


@dataclass
class Range:
    start_byte: int
    end_byte: int
    start_point: Point
    end_point: Point


@dataclass
class PiranhaMatch:
    range: Range
    matches: dict[str, str]


@dataclass
class PiranhaEdit:
    p_match: PiranhaMatch
    replacement_string: str
    matched_rule: str


@dataclass
class PiranhaOutputSummary:
    path: str
    content: str
    matches: list[(str, PiranhaMatch)]
    rewrites: list[PiranhaEdit]
