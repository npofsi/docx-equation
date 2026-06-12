# Tutorial: Generate a DOCX with Equations from Scratch

This tutorial creates a DOCX file with `python-docx` and registers equations
with `docx-equation` while the document is being composed. The recommended API
uses `EquationRegistry`, so application code does not need to create or track
placeholder strings directly. The registry uses hidden internal anchors during
the save step. The same MathML source can produce native Word OMML output or
MathType-compatible output.

## 1. Install

```bash
python3 -m pip install docx-equation
```

For repository development:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

`python-docx` is installed as a dependency of `docx-equation`.

## 2. Create a Document and Registry

Create the document and a registry before adding equation-bearing content.

```python
from docx import Document
from docx_equation import EquationRegistry

doc = Document()
equations = EquationRegistry()

doc.add_heading("Equation tutorial", level=1)
```

## 3. Prepare MathML

MathML can be kept in variables and registered where it belongs in the document.
Inline equations omit the `number` field. Display equations can include a
number and use the shared tabbed layout.

```python
inline_mathml = """
<math xmlns="http://www.w3.org/1998/Math/MathML">
  <mi>E</mi><mo>=</mo><mi>P</mi><mi>t</mi>
</math>
"""

display_mathml = """
<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">
  <msubsup>
    <mi>P</mi>
    <mrow><mi>e</mi><mi>s</mi></mrow>
    <mrow><mi>c</mi><mi>h</mi></mrow>
  </msubsup>
  <mo>(</mo><mi>t</mi><mo>)</mo>
  <mo>=</mo>
  <mfrac>
    <mn>1</mn>
    <mrow><mn>1</mn><mo>+</mo><mi>s</mi><mi>T</mi></mrow>
  </mfrac>
</math>
"""

p = doc.add_paragraph("Inline energy balance: ")
equations.add_inline(p, inline_mathml)
p.add_run(".")

doc.add_paragraph("Display equation:")
equations.add_display(doc, display_mathml, number=1)
```

## 4. Export Native Word OMML

OMML output keeps equations editable with Word's native equation engine.

```python
from docx_equation import (
    EquationStyle,
    ExportOptions,
    NumberingOptions,
    OmmlOptions,
)

style = EquationStyle(
    font_family="Times New Roman",
    east_asia_font="SimSun",
    font_size_pt=10.5,
    number_font_size_pt=10.5,
)

numbering = NumberingOptions(
    chapter=1,
    number_format="(1SEP1)",
    separator="-",
    sequence_name="Eq",
)

summary = equations.save(
    doc,
    "tutorial_omml.docx",
    ExportOptions(
        target="omml",
        style=style,
        numbering=numbering,
        omml=OmmlOptions(font_family="Times New Roman", east_asia_font="SimSun"),
    ),
)

print(summary)
```

The display equation is centered with a tab stop, while the label is right
aligned. With the options above, the label is `(1-1)`.

Use a sequence-only label by changing the numbering options:

```python
NumberingOptions(number_format="(1)")
```

## 5. Export MathType-Compatible Objects

MathType output embeds OLE objects. The default `alternate-content` mode embeds
a MathType object and keeps an OMML fallback for Word environments without
MathType.

```python
from docx_equation import MathTypeOptions

summary = equations.save(
    doc,
    "tutorial_mathtype.docx",
    ExportOptions(
        target="mathtype",
        style=style,
        numbering=numbering,
        mathtype=MathTypeOptions(
            embed_mode="alternate-content",
            mathtype_version="DSMT4",
        ),
        omml=OmmlOptions(font_family="Times New Roman", east_asia_font="SimSun"),
    ),
)

print(summary)
```

Use `embed_mode="png-preview"` when the document should force the embedded OLE
preview path without an OMML fallback branch.

## 6. Complete Script

```python
from docx import Document

from docx_equation import (
    EquationRegistry,
    EquationStyle,
    ExportOptions,
    MathTypeOptions,
    NumberingOptions,
    OmmlOptions,
)

doc = Document()
equations = EquationRegistry()
doc.add_heading("Equation tutorial", level=1)
p = doc.add_paragraph("Inline energy balance: ")
equations.add_inline(
    p,
    "<math xmlns='http://www.w3.org/1998/Math/MathML'><mi>E</mi><mo>=</mo><mi>P</mi><mi>t</mi></math>",
)
doc.add_paragraph("Display equation:")
equations.add_display(
    doc,
    "<math xmlns='http://www.w3.org/1998/Math/MathML'><mfrac><mi>a</mi><mi>b</mi></mfrac><mo>=</mo><mi>c</mi></math>",
    number=1,
)

style = EquationStyle(font_family="Times New Roman", east_asia_font="SimSun")
numbering = NumberingOptions(chapter=1, number_format="(1SEP1)", separator="-")

equations.save(
    doc,
    "tutorial_omml.docx",
    ExportOptions(target="omml", style=style, numbering=numbering),
)

equations.save(
    doc,
    "tutorial_mathtype.docx",
    ExportOptions(
        target="mathtype",
        style=style,
        numbering=numbering,
        mathtype=MathTypeOptions(embed_mode="alternate-content"),
        omml=OmmlOptions(font_family="Times New Roman", east_asia_font="SimSun"),
    ),
)
```

## 7. Inspect the Result

Use the CLI to count generated equation structures:

```bash
docx-equation inspect tutorial_omml.docx
docx-equation inspect tutorial_mathtype.docx
```
