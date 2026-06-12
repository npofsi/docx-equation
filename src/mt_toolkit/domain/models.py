from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


EmbedMode = Literal["alternate-content", "png-preview"]
MathTypeVersion = Literal["DSMT4", "DSMT6"]
DisplayLayout = Literal["preserve", "tabbed"]


@dataclass(frozen=True)
class ConversionOptions:
    embed_mode: EmbedMode = "alternate-content"
    mathtype_version: MathTypeVersion = "DSMT4"
    display_layout: DisplayLayout = "tabbed"
    inline_height_pt: float = 12.5
    display_height_pt: float = 21.0
    max_width_pt: float = 360.0
    preview_pt_per_px: float | None = 0.15
    chrome_path: str | Path | None = None

    @property
    def prog_id(self) -> str:
        return f"Equation.{self.mathtype_version}"


@dataclass(frozen=True)
class ConversionError:
    index: int
    placeholder: str | None
    message: str


@dataclass
class ConversionSummary:
    found: int = 0
    converted: int = 0
    skipped: int = 0
    errors: list[ConversionError] = field(default_factory=list)

    def add_error(self, index: int, placeholder: str | None, message: str) -> None:
        self.skipped += 1
        self.errors.append(ConversionError(index=index, placeholder=placeholder, message=message))


@dataclass(frozen=True)
class EquationSpec:
    placeholder: str
    mathml: str
    display: bool = False
