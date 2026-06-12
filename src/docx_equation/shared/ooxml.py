from __future__ import annotations

from lxml import etree


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "o": "urn:schemas-microsoft-com:office:office",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
}

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
IMAGE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
OLE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject"


def q(name: str) -> str:
    prefix, local = name.split(":", 1)
    return f"{{{NS[prefix]}}}{local}"


def add_relationship(root: etree._Element, rel_type: str, target: str, prefix: str = "rIdEq") -> str:
    existing = {rel.get("Id") for rel in root.findall(f"{{{REL_NS}}}Relationship")}
    index = 1
    while f"{prefix}{index}" in existing:
        index += 1
    rel_id = f"{prefix}{index}"
    etree.SubElement(
        root,
        f"{{{REL_NS}}}Relationship",
        {"Id": rel_id, "Type": rel_type, "Target": target},
    )
    return rel_id


def ensure_default(root: etree._Element, extension: str, content_type: str) -> None:
    if not root.xpath(f'ct:Default[@Extension="{extension}"]', namespaces={"ct": CT_NS}):
        etree.SubElement(root, f"{{{CT_NS}}}Default", {"Extension": extension, "ContentType": content_type})


def find_placeholder_run(root: etree._Element, placeholder: str) -> etree._Element:
    for run in root.xpath("//w:r", namespaces=NS):
        text = "".join(run.xpath(".//w:t/text()", namespaces=NS))
        if text == placeholder:
            return run
    raise ValueError(f"Placeholder run was not found: {placeholder}")


def ancestor(element: etree._Element, tag: str) -> etree._Element | None:
    parent = element.getparent()
    while parent is not None:
        if parent.tag == tag:
            return parent
        parent = parent.getparent()
    return None


def ancestor_paragraph(element: etree._Element) -> etree._Element | None:
    return ancestor(element, q("w:p"))


def document_text_width_dxa(root: etree._Element, default: int = 9360) -> int:
    sections = root.xpath("//w:sectPr", namespaces=NS)
    if not sections:
        return default
    section = sections[-1]
    page_width = section.xpath("./w:pgSz/@w:w", namespaces=NS)
    left = section.xpath("./w:pgMar/@w:left", namespaces=NS)
    right = section.xpath("./w:pgMar/@w:right", namespaces=NS)
    try:
        return int(page_width[0]) - int(left[0]) - int(right[0])
    except (IndexError, TypeError, ValueError):
        return default
