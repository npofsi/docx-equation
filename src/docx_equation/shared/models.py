from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


EmbedMode = Literal["alternate-content", "png-preview"]
MathTypeVersion = Literal["DSMT4", "DSMT6"]
DisplayLayout = Literal["preserve", "tabbed"]
ExportTarget = Literal["omml", "mathtype"]
NumberingFormat = Literal["(1)", "(1SEP1)"]


@dataclass(frozen=True)
class EquationStyle:
    font_family: str = "Times New Roman"
    east_asia_font: str = "SimSun"
    font_size_pt: float = 10.5
    number_font_size_pt: float = 10.5
    color: str = "000000"


@dataclass(frozen=True)
class NumberingOptions:
    enabled: bool = True
    layout: Literal["tabbed"] = "tabbed"
    number_format: NumberingFormat = "(1SEP1)"
    chapter: int | None = None
    sequence_name: str = "Eq"
    separator: str = "-"
    use_seq_field: bool = True
    restart_at_first: bool = True
    center_tab_ratio: float = 0.5
    before_dxa: int = 80
    after_dxa: int = 80
    text_width_dxa: int | None = None


@dataclass(frozen=True)
class OmmlOptions:
    display: bool = False
    font_family: str | None = None
    east_asia_font: str | None = None


@dataclass(frozen=True)
class MathTypeOptions:
    embed_mode: EmbedMode = "alternate-content"
    mathtype_version: MathTypeVersion = "DSMT4"
    inline_height_pt: float = 12.5
    display_height_pt: float = 21.0
    max_width_pt: float = 360.0
    preview_font_px: int = 38
    preview_pt_per_px: float | None = 0.15
    chrome_path: str | Path | None = None

    @property
    def prog_id(self) -> str:
        return f"Equation.{self.mathtype_version}"


@dataclass(frozen=True)
class ExportOptions:
    target: ExportTarget = "mathtype"
    display_layout: DisplayLayout = "tabbed"
    style: EquationStyle = field(default_factory=EquationStyle)
    numbering: NumberingOptions = field(default_factory=NumberingOptions)
    omml: OmmlOptions = field(default_factory=OmmlOptions)
    mathtype: MathTypeOptions = field(default_factory=MathTypeOptions)


@dataclass(frozen=True)
class ConversionOptions:
    target: ExportTarget = "mathtype"
    embed_mode: EmbedMode = "alternate-content"
    mathtype_version: MathTypeVersion = "DSMT4"
    display_layout: DisplayLayout = "tabbed"
    inline_height_pt: float = 12.5
    display_height_pt: float = 21.0
    max_width_pt: float = 360.0
    preview_font_px: int = 38
    preview_pt_per_px: float | None = 0.15
    chrome_path: str | Path | None = None
    style: EquationStyle = field(default_factory=EquationStyle)
    numbering: NumberingOptions = field(default_factory=NumberingOptions)
    omml: OmmlOptions = field(default_factory=OmmlOptions)

    @property
    def prog_id(self) -> str:
        return f"Equation.{self.mathtype_version}"

    @property
    def mathtype(self) -> MathTypeOptions:
        return MathTypeOptions(
            embed_mode=self.embed_mode,
            mathtype_version=self.mathtype_version,
            inline_height_pt=self.inline_height_pt,
            display_height_pt=self.display_height_pt,
            max_width_pt=self.max_width_pt,
            preview_font_px=self.preview_font_px,
            preview_pt_per_px=self.preview_pt_per_px,
            chrome_path=self.chrome_path,
        )

    def to_export_options(self, target: ExportTarget | None = None) -> ExportOptions:
        return ExportOptions(
            target=target or self.target,
            display_layout=self.display_layout,
            style=self.style,
            numbering=self.numbering,
            omml=self.omml,
            mathtype=self.mathtype,
        )


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
    number: int | str | None = None


OptionsLike = ExportOptions | ConversionOptions | MathTypeOptions | OmmlOptions | None


def normalize_options(options: OptionsLike = None, target: ExportTarget = "mathtype") -> ExportOptions:
    if options is None:
        return ExportOptions(target=target)
    if isinstance(options, ExportOptions):
        return options
    if isinstance(options, ConversionOptions):
        return options.to_export_options(target=target if options.target == "mathtype" and target == "omml" else None)
    if isinstance(options, MathTypeOptions):
        return ExportOptions(target="mathtype", mathtype=options)
    if isinstance(options, OmmlOptions):
        return ExportOptions(target="omml", omml=options)
    raise TypeError(f"Unsupported options type: {type(options)!r}")
