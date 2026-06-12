from __future__ import annotations

from lxml import etree

from docx_equation.shared.models import OmmlOptions


MATHML_NS = "http://www.w3.org/1998/Math/MathML"
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def mathml_to_omml(data: bytes | str, display: bool = False, options: OmmlOptions | None = None) -> etree._Element:
    opts = options or OmmlOptions()
    root = _parse(data)
    omath = _el("m:oMath")
    _append_children(omath, root)
    result = omath
    if display:
        para = _el("m:oMathPara")
        para.append(omath)
        result = para
    _apply_math_fonts(result, opts)
    return result


def mathml_to_omml_xml(data: bytes | str, display: bool = False, options: OmmlOptions | None = None) -> bytes:
    return etree.tostring(mathml_to_omml(data, display=display, options=options), encoding="utf-8")


def _parse(data: bytes | str) -> etree._Element:
    if isinstance(data, str):
        data = data.encode("utf-8")
    parser = etree.XMLParser(resolve_entities=False, recover=True, remove_blank_text=True)
    return etree.fromstring(data, parser)


def _append_children(parent: etree._Element, element: etree._Element) -> None:
    tag = _local(element)
    if tag in {"math", "mrow", "mstyle", "mpadded", "semantics", "mtd"}:
        children = [child for child in element if _local(child) != "annotation"]
        index = 0
        while index < len(children):
            child = children[index]
            if _is_big_operator_limit(child) and index + 1 < len(children):
                parent.append(_nary_from_limit(child, children[index + 1]))
                index += 2
                continue
            _append_children(parent, child)
            index += 1
        return
    converted = _convert_element(element)
    if converted is not None:
        parent.append(converted)


def _convert_element(element: etree._Element) -> etree._Element | None:
    tag = _local(element)
    if tag in {"mi", "mn", "mo", "mtext"}:
        style = "i" if tag == "mi" else "p"
        return _run(_text(element), style)
    if tag == "mspace":
        return _run(" ", "p")
    if tag == "msub" and len(element) >= 2:
        return _script("m:sSub", element[0], sub=element[1])
    if tag == "msup" and len(element) >= 2:
        return _script("m:sSup", element[0], sup=element[1])
    if tag == "msubsup" and len(element) >= 3:
        return _script("m:sSubSup", element[0], sub=element[1], sup=element[2])
    if tag == "mfrac" and len(element) >= 2:
        frac = _el("m:f")
        frac.append(_ctrl_pr_container("m:fPr"))
        num = _container("m:num", element[0])
        den = _container("m:den", element[1])
        frac.extend([num, den])
        return frac
    if tag == "msqrt":
        rad = _el("m:rad")
        rad_pr = _el("m:radPr")
        deg_hide = _el("m:degHide")
        deg_hide.set(_qn("m:val"), "1")
        rad_pr.extend([deg_hide, _ctrl_pr()])
        rad.extend([rad_pr, _el("m:deg"), _container("m:e", element)])
        return rad
    if tag == "mroot" and len(element) >= 2:
        rad = _el("m:rad")
        rad.append(_ctrl_pr_container("m:radPr"))
        rad.extend([_container("m:deg", element[1]), _container("m:e", element[0])])
        return rad
    if tag == "mfenced":
        return _delimiter(element, element.get("open", "("), element.get("close", ")"))
    if tag in {"munder", "mover", "munderover"}:
        return _under_over(element)
    if tag == "mtable":
        return _matrix(element)
    if tag in {"mtr", "mlabeledtr"}:
        row = _el("m:mr")
        for cell in element:
            if _local(cell) == "mtd":
                row.append(_container("m:e", cell))
        return row
    if tag == "menclose":
        return _enclose(element)
    container = _el("m:e")
    _append_children(container, element)
    if len(container):
        return container
    text = _text(element)
    return _run(text, "p") if text else None


def _script(tag: str, base: etree._Element, sub: etree._Element | None = None, sup: etree._Element | None = None) -> etree._Element:
    node = _el(tag)
    node.append(_container("m:e", base))
    if sub is not None:
        node.append(_container("m:sub", sub))
    if sup is not None:
        node.append(_container("m:sup", sup))
    return node


def _delimiter(element: etree._Element, begin: str, end: str) -> etree._Element:
    node = _el("m:d")
    props = _el("m:dPr")
    beg = _el("m:begChr")
    beg.set(_qn("m:val"), begin)
    end_el = _el("m:endChr")
    end_el.set(_qn("m:val"), end)
    grow = _el("m:grow")
    grow.set(_qn("m:val"), "1")
    props.extend([beg, end_el, grow, _ctrl_pr()])
    body = _el("m:e")
    for child in element:
        _append_children(body, child)
    node.extend([props, body])
    return node


def _under_over(element: etree._Element) -> etree._Element:
    base = element[0] if len(element) else None
    base_text = _operator_text(base) if base is not None else ""
    if base_text in {"∑", "∏", "∫", "∬", "∭"}:
        return _nary_from_limit(element, None)
    if _local(element) == "mover" and len(element) >= 2:
        accent = _operator_text(element[1])
        if accent in {"¯", "‾", "\u0305"}:
            bar = _el("m:bar")
            props = _el("m:barPr")
            pos = _el("m:pos")
            pos.set(_qn("m:val"), "top")
            props.extend([pos, _ctrl_pr()])
            bar.extend([props, _container("m:e", element[0])])
            return bar
    if _local(element) == "munder" and len(element) >= 2:
        accent = _operator_text(element[1])
        if accent in {"_", "‾", "\u0332"}:
            bar = _el("m:bar")
            props = _el("m:barPr")
            pos = _el("m:pos")
            pos.set(_qn("m:val"), "bot")
            props.extend([pos, _ctrl_pr()])
            bar.extend([props, _container("m:e", element[0])])
            return bar
    if _local(element) == "munderover" and len(element) >= 3:
        return _script("m:sSubSup", element[0], sub=element[1], sup=element[2])
    if _local(element) == "munder" and len(element) >= 2:
        return _script("m:sSub", element[0], sub=element[1])
    if _local(element) == "mover" and len(element) >= 2:
        return _script("m:sSup", element[0], sup=element[1])
    return _container("m:e", element)


def _is_big_operator_limit(element: etree._Element) -> bool:
    if _local(element) not in {"munder", "mover", "munderover"} or len(element) == 0:
        return False
    return _operator_text(element[0]) in {"∑", "∏", "∫", "∬", "∭"}


def _nary_from_limit(element: etree._Element, body_source: etree._Element | None) -> etree._Element:
    tag = _local(element)
    operator = _operator_text(element[0])
    sub_source = element[1] if tag in {"munder", "munderover"} and len(element) > 1 else None
    sup_source = None
    if tag == "mover" and len(element) > 1:
        sup_source = element[1]
    elif tag == "munderover" and len(element) > 2:
        sup_source = element[2]

    node = _el("m:nary")
    props = _el("m:naryPr")
    chr_el = _el("m:chr")
    chr_el.set(_qn("m:val"), operator)
    lim = _el("m:limLoc")
    lim.set(_qn("m:val"), "undOvr")
    sub_hide = _el("m:subHide")
    sub_hide.set(_qn("m:val"), "0" if sub_source is not None else "1")
    sup_hide = _el("m:supHide")
    sup_hide.set(_qn("m:val"), "0" if sup_source is not None else "1")
    props.extend([chr_el, lim, sub_hide, sup_hide, _ctrl_pr()])
    node.append(props)
    node.append(_container("m:sub", sub_source) if sub_source is not None else _el("m:sub"))
    node.append(_container("m:sup", sup_source) if sup_source is not None else _el("m:sup"))
    node.append(_container("m:e", body_source) if body_source is not None else _el("m:e"))
    return node


def _matrix(element: etree._Element) -> etree._Element:
    matrix = _el("m:m")
    matrix.append(_ctrl_pr_container("m:mPr"))
    for row in element:
        if _local(row) in {"mtr", "mlabeledtr"}:
            converted = _convert_element(row)
            if converted is not None:
                matrix.append(converted)
    return matrix


def _enclose(element: etree._Element) -> etree._Element:
    notation = element.get("notation", "")
    if "box" in notation or "roundedbox" in notation:
        box = _el("m:borderBox")
        box.append(_ctrl_pr_container("m:borderBoxPr"))
        box.append(_container("m:e", element))
        return box
    body = _container("m:e", element)
    bar = _el("m:bar")
    props = _el("m:barPr")
    pos = _el("m:pos")
    pos.set(_qn("m:val"), "bot" if "bottom" in notation or "underline" in notation else "top")
    props.extend([pos, _ctrl_pr()])
    bar.extend([props, body])
    return bar


def _container(tag: str, source: etree._Element | None) -> etree._Element:
    node = _el(tag)
    if source is not None:
        if _local(source) in {"math", "mrow", "mstyle", "mpadded", "mtd", "menclose"}:
            for child in source:
                if _local(child) != "annotation":
                    _append_children(node, child)
        else:
            converted = _convert_element(source)
            if converted is not None:
                node.append(converted)
    return node


def _run(text: str, style: str) -> etree._Element:
    node = _el("m:r")
    rpr = _el("m:rPr")
    sty = _el("m:sty")
    sty.set(_qn("m:val"), style)
    rpr.append(sty)
    node.append(rpr)
    node.append(_math_run_properties())
    text_el = _el("m:t")
    if text.startswith(" ") or text.endswith(" "):
        text_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_el.text = text
    node.append(text_el)
    return node


def _ctrl_pr_container(tag: str) -> etree._Element:
    node = _el(tag)
    node.append(_ctrl_pr())
    return node


def _ctrl_pr() -> etree._Element:
    ctrl = _el("m:ctrlPr")
    ctrl.append(_math_run_properties())
    return ctrl


def _math_run_properties() -> etree._Element:
    rpr = _el("w:rPr")
    fonts = _el("w:rFonts")
    fonts.set(_qn("w:ascii"), "Times New Roman")
    fonts.set(_qn("w:hAnsi"), "Times New Roman")
    fonts.set(_qn("w:cs"), "Times New Roman")
    fonts.set(_qn("w:eastAsia"), "Times New Roman")
    rpr.append(fonts)
    return rpr


def _apply_math_fonts(root: etree._Element, options: OmmlOptions) -> None:
    font = options.font_family or "Times New Roman"
    east_asia = options.east_asia_font or font
    for fonts in root.xpath(".//w:rFonts", namespaces={"w": W_NS}):
        fonts.set(_qn("w:ascii"), font)
        fonts.set(_qn("w:hAnsi"), font)
        fonts.set(_qn("w:cs"), font)
        fonts.set(_qn("w:eastAsia"), east_asia)


def _operator_text(element: etree._Element | None) -> str:
    if element is None:
        return ""
    tag = _local(element)
    if tag in {"mo", "mi", "mn", "mtext"}:
        return _text(element).strip()
    if len(element) == 1:
        return _operator_text(element[0])
    return ""


def _text(element: etree._Element) -> str:
    return "".join(element.itertext()).replace("\u00a0", " ")


def _local(element: etree._Element) -> str:
    return etree.QName(element).localname


def _el(name: str) -> etree._Element:
    prefix, local = name.split(":", 1)
    namespace = {"m": OMML_NS, "w": W_NS}[prefix]
    return etree.Element(f"{{{namespace}}}{local}")


def _qn(name: str) -> str:
    prefix, local = name.split(":", 1)
    namespace = {"m": OMML_NS, "w": W_NS}[prefix]
    return f"{{{namespace}}}{local}"
