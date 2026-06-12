# mt-toolkit

`mt-toolkit` is a Python package for generating MathType-compatible equation objects and DOCX equation layouts from MathML.

## Features

- Parse MathML into the package equation AST.
- Encode equations as MathType MTEF bytes.
- Build `Equation.DSMT4` OLE compound objects by default.
- Optionally build `Equation.DSMT6` objects.
- Convert MathML into Word OMML.
- Embed MathML equations into DOCX packages as MathType OLE objects.
- Preserve Word display through `mc:AlternateContent` with OMML fallback.
- Create PNG-preview MathType objects when explicit preview rendering is required.
- Provide a CLI for MathML artifact generation, DOCX demos, DOCX inspection, and legacy OMML conversion.

## Install

```bash
python3 -m pip install mt-toolkit
```

For local development:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

## Python API

```python
from mt_toolkit import ConversionOptions, mathml_to_mathtype_ole, mathml_to_omml

mathml = """<math xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><mi>a</mi><mi>b</mi></mfrac>
</math>"""

ole_bytes = mathml_to_mathtype_ole(mathml)
omml_element = mathml_to_omml(mathml)

ole_dsmt6 = mathml_to_mathtype_ole(
    mathml,
    ConversionOptions(mathtype_version="DSMT6"),
)
```

Embed MathML placeholders in a DOCX:

```python
from mt_toolkit import ConversionOptions, EquationSpec, embed_mathml_placeholders

summary = embed_mathml_placeholders(
    "input_with_placeholders.docx",
    "output_mathtype.docx",
    [
        EquationSpec(
            placeholder="{{MT_EQ_001}}",
            mathml="<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>x</mi></math>",
            display=False,
        )
    ],
    ConversionOptions(embed_mode="alternate-content", mathtype_version="DSMT4"),
)
```

## Command Line

Generate MTEF and OLE from MathML:

```bash
mt-toolkit mathml equation.mml --mtef output/equation.mtef --ole output/oleObject1.bin
```

Build a demo DOCX from MathML files:

```bash
mt-toolkit demo equation_001.mml equation_002.mml -o output/demo.docx
```

Inspect a DOCX:

```bash
mt-toolkit inspect output/demo.docx
```

Run the legacy OMML conversion entry point:

```bash
mt-toolkit convert input.docx -o output.docx --display-layout tabbed
```

## Build

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m build
python3 -m twine check dist/*
```

## CI And Publishing

The GitHub Actions workflow runs tests and builds distributions on pushes and pull requests. The publish job is manual and runs only through `workflow_dispatch` after PyPI trusted publishing has been configured.
