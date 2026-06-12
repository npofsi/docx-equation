# docx-equation

`docx-equation` builds DOCX equation content from MathML. It can export Word OMML equations or MathType-compatible OLE objects and uses shared layout helpers for numbered display equations.

## Features

- MathML parsing into a shared equation AST.
- MathML to Word OMML conversion.
- MathML to MathType MTEF and `Equation.DSMT4` OLE objects.
- Optional `Equation.DSMT6` OLE generation.
- DOCX placeholder replacement for OMML or MathType output.
- `mc:AlternateContent` MathType embedding with OMML fallback.
- PNG-preview MathType embedding.
- Shared tabbed display-equation numbering with centered formulas and right-aligned labels.
- Configurable export options for target format, fonts, font sizes, MathType version, preview sizing, and numbering.

## Install

```bash
python3 -m pip install docx-equation
```

For local development:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## Package Layout

```text
docx_equation.shared      MathML parser, LaTeX subset parser, models, numbering helpers
docx_equation.omml        MathML to OMML conversion and DOCX embedding
docx_equation.mathtype    MTEF/OLE generation, preview rendering, DOCX embedding
docx_equation.api         Public routing API for selected export targets
docx_equation.cli         Command-line interface
```

## Python API

Create OMML or MathType output from the same MathML placeholders:

```python
from docx_equation import (
    EquationSpec,
    EquationStyle,
    ExportOptions,
    MathTypeOptions,
    NumberingOptions,
    OmmlOptions,
    embed_mathml_placeholders,
)

equations = [
    EquationSpec(
        placeholder="{{DOCX_EQ_001}}",
        mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>x</mi></math>",
        display=True,
        number=1,
    )
]

common = {
    "style": EquationStyle(
        font_family="Times New Roman",
        east_asia_font="SimSun",
        font_size_pt=10.5,
        number_font_size_pt=10.5,
    ),
    "numbering": NumberingOptions(chapter=4, sequence_name="Eq"),
}

embed_mathml_placeholders(
    "input.docx",
    "output_omml.docx",
    equations,
    ExportOptions(target="omml", omml=OmmlOptions(font_family="Times New Roman"), **common),
)

embed_mathml_placeholders(
    "input.docx",
    "output_mathtype.docx",
    equations,
    ExportOptions(
        target="mathtype",
        mathtype=MathTypeOptions(embed_mode="alternate-content", mathtype_version="DSMT4"),
        **common,
    ),
)
```

Number display can use a sequence-only format or a chapter-sequence format. `SEP` is controlled by `separator` and defaults to `"-"`:

```python
NumberingOptions(number_format="(1)")
NumberingOptions(chapter=4, number_format="(1SEP1)", separator="-")
```

Build standalone equation documents:

```python
from docx_equation import ExportOptions, NumberingOptions, build_equation_docx

mathml_items = [
    "<math xmlns='http://www.w3.org/1998/Math/MathML'><mfrac><mi>a</mi><mi>b</mi></mfrac></math>"
]

build_equation_docx(
    mathml_items,
    "equations.docx",
    ExportOptions(target="mathtype", numbering=NumberingOptions(chapter=1)),
)
```

Generate raw objects:

```python
from docx_equation import mathml_to_mathtype_ole, mathml_to_omml

mathml = "<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>x</mi></math>"
ole_bytes = mathml_to_mathtype_ole(mathml)
omml_element = mathml_to_omml(mathml)
```

## Command Line

Generate MTEF, OLE, or OMML artifacts:

```bash
docx-equation mathml equation.mml --mtef equation.mtef --ole oleObject1.bin --omml equation.omml
```

Build a DOCX from MathML files:

```bash
docx-equation demo equation_001.mml equation_002.mml -o equations.docx --target mathtype --chapter 4
```

Convert a DOCX:

```bash
docx-equation convert input.docx -o output.docx --embed-mode alternate-content
```

Select display-equation numbering:

```bash
docx-equation demo equation_001.mml -o equations.docx --chapter 4 --number-format "(1SEP1)" --number-separator "-"
docx-equation demo equation_001.mml -o equations.docx --number-format "(1)"
```

Inspect a DOCX:

```bash
docx-equation inspect output.docx
```

## Build

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m build
python3 -m twine check dist/*
```

## Documentation

Developer documentation lives in `docs/`.

- `docs/tutorial.md` shows how to create a DOCX with equations from scratch.
- `docs/api/index.html` links to the `pydoc` API reference.

Regenerate API documentation:

```bash
python3 docs/generate_pydoc.py
```

## License

`docx-equation` is distributed under the GNU Affero General Public License v3.0 only (`AGPL-3.0-only`).

## CI

GitHub Actions runs `pytest`, `python -m build`, and `twine check dist/*` on pushes and pull requests. PyPI publishing uses Trusted Publishing with the `pypi` GitHub environment. The publish job runs after CI on `v*` tag pushes, and it can also be started with `workflow_dispatch` when `publish` is set to `true`.
