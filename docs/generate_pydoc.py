"""Generate pydoc HTML files for docx-equation."""

from __future__ import annotations

from html import escape
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
API_DIR = DOCS_DIR / "api"

MODULES = [
    "docx_equation",
    "docx_equation.api",
    "docx_equation.cli",
    "docx_equation.shared",
    "docx_equation.shared.models",
    "docx_equation.shared.mathml",
    "docx_equation.shared.latex",
    "docx_equation.shared.numbering",
    "docx_equation.shared.ooxml",
    "docx_equation.omml",
    "docx_equation.omml.converter",
    "docx_equation.omml.embed",
    "docx_equation.mathtype",
    "docx_equation.mathtype.mtef",
    "docx_equation.mathtype.ole",
    "docx_equation.mathtype.cfb",
    "docx_equation.mathtype.ooxml",
    "docx_equation.mathtype.embed",
    "docx_equation.mathtype.legacy",
    "docx_equation.mathtype.preview",
]


def main() -> int:
    if API_DIR.exists():
        shutil.rmtree(API_DIR)
    API_DIR.mkdir(parents=True)

    env = os.environ.copy()
    source_path = str(ROOT / "src")
    env["PYTHONPATH"] = source_path if not env.get("PYTHONPATH") else source_path + os.pathsep + env["PYTHONPATH"]

    subprocess.run([sys.executable, "-m", "pydoc", "-w", *MODULES], cwd=API_DIR, env=env, check=True)
    _relativize_file_links()
    _write_api_index()
    return 0


def _relativize_file_links() -> None:
    root_posix = ROOT.as_posix()
    for html_path in API_DIR.glob("*.html"):
        html = html_path.read_text(encoding="utf-8")
        html = html.replace(f'href="file:{root_posix}/', 'href="../../')
        html = html.replace(f">{root_posix}/", ">")
        html_path.write_text(html, encoding="utf-8")


def _write_api_index() -> None:
    links = "\n".join(
        f'      <li><a href="{escape(module)}.html">{escape(module)}</a></li>' for module in MODULES
    )
    (API_DIR / "index.html").write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>docx-equation API Reference</title>
</head>
<body>
  <h1>docx-equation API Reference</h1>
  <p>Generated with <code>python -m pydoc</code>.</p>
  <ul>
{links}
  </ul>
</body>
</html>
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())

