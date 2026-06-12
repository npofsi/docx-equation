# docx-equation Documentation

`docx-equation` generates DOCX equations from MathML. The package can emit
native Word OMML equations or MathType-compatible OLE objects, and both export
paths share the same placeholder, layout, and numbering configuration.

## Guides

- [Tutorial: generate a DOCX with equations from scratch](tutorial.md)

## API Reference

The API reference is generated with Python's standard `pydoc` tool.

- [pydoc API index](api/index.html)
- [top-level package](api/docx_equation.html)
- [public API](api/docx_equation.api.html)
- [shared configuration models](api/docx_equation.shared.models.html)
- [numbering helpers](api/docx_equation.shared.numbering.html)
- [OMML converter](api/docx_equation.omml.converter.html)
- [MathType embedder](api/docx_equation.mathtype.embed.html)

Regenerate the API reference after changing public modules:

```bash
python3 docs/generate_pydoc.py
```

