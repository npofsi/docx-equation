# mt-toolkit

`mt-toolkit` is a Python package for creating MathType-compatible equation artifacts. It can encode a supported formula tree to MTEF, wrap MTEF data in a legacy OLE compound file, render equation previews, and replace DOCX OMML equations with embedded MathType-style objects.

## Features

- Encode a supported equation AST to MathType MTEF bytes.
- Build `Equation.DSMT4` OLE compound objects.
- Parse a practical subset of LaTeX into the package AST.
- Parse MathML structures including fractions, roots, scripts, fenced expressions, accents, large operators, matrices, and piles.
- Render MathML previews to PNG with a headless Chrome executable.
- Convert DOCX OMML equations to embedded OLE objects with PNG previews.
- Create display-equation paragraphs with centered formulas and right-aligned equation numbers.

## Install

```bash
python -m pip install mt-toolkit
```

For local development:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Command Line

Create MTEF and OLE files from a formula:

```bash
mt-toolkit "\\frac{1}{2}+x_i" --out output
```

Create a demo DOCX:

```bash
mt-toolkit "F_n=F_{n-1}+F_{n-2}" --docx output/demo.docx
```

Convert a DOCX:

```bash
mt-toolkit \
  --convert-docx input.docx \
  --converted-docx output.docx \
  --work-dir output/work \
  --display-layout tabbed
```

## Python API

```python
from mt_toolkit import encode_mtef, parse_latex_subset, build_mathtype_ole_object

expr = parse_latex_subset(r"\sum_{i=1}^{n} x_i")
mtef = encode_mtef(expr)
ole_bytes = build_mathtype_ole_object(mtef)
```

## Build

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m build
python -m twine check dist/*
```

## CI And Publishing

The GitHub Actions workflow runs tests and builds distributions on pushes and pull requests. The publish job is manual and runs only when the workflow is dispatched with `publish` enabled after PyPI trusted publishing has been configured.
