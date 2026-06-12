from __future__ import annotations

from dataclasses import dataclass

from .mtef import BigOperator, Expr, Fraction, Hat, Overbar, Sequence, Sqrt, Subscript, Subsup, Superscript, Symbol, Text, Underbar, seq


GREEK = {
    "alpha": "\u03b1",
    "beta": "\u03b2",
    "gamma": "\u03b3",
    "delta": "\u03b4",
    "epsilon": "\u03b5",
    "lambda": "\u03bb",
    "mu": "\u03bc",
    "pi": "\u03c0",
    "tau": "\u03c4",
    "sigma": "\u03c3",
    "theta": "\u03b8",
    "omega": "\u03c9",
    "Delta": "\u0394",
    "Omega": "\u03a9",
    "eta": "\u03b7",
}

SYMBOLS = {
    "times": "\u00d7",
    "div": "\u00f7",
    "cdot": "\u00d7",
    "le": "\u2264",
    "leq": "\u2264",
    "ge": "\u2265",
    "geq": "\u2265",
    "in": "\u2208",
    "pm": "\u00b1",
    "mp": "\u2213",
    "neq": "\u2260",
    "approx": "\u2248",
}


def parse_latex_subset(source: str) -> Expr:
    parser = _Parser(source)
    result = parser.parse_until()
    parser.skip_spaces()
    if not parser.done:
        raise ValueError(f"Unexpected input at offset {parser.index}: {source[parser.index:]!r}")
    return result


@dataclass
class _Parser:
    source: str
    index: int = 0

    @property
    def done(self) -> bool:
        return self.index >= len(self.source)

    def parse_until(self, terminator: str | None = None) -> Expr:
        items: list[Expr] = []
        while not self.done:
            if terminator and self.peek() == terminator:
                break
            self.skip_spaces()
            if self.done or (terminator and self.peek() == terminator):
                break
            atom = self.parse_atom()
            subscript: Expr | None = None
            superscript: Expr | None = None
            while not self.done and self.peek() in "_^":
                marker = self.take()
                script = self.parse_script()
                if marker == "_":
                    subscript = script
                else:
                    superscript = script
            if subscript is not None or superscript is not None:
                if isinstance(atom, BigOperator):
                    atom = BigOperator(atom.operator, atom.body, lower=subscript, upper=superscript)
                elif subscript is not None and superscript is not None:
                    atom = Subsup(atom, subscript, superscript)
                elif subscript is not None:
                    atom = Subscript(atom, subscript)
                elif superscript is not None:
                    atom = Superscript(atom, superscript)
            items.append(atom)
        return seq(items) if items else Text("")

    def parse_atom(self) -> Expr:
        char = self.peek()
        if char == "{":
            return self.parse_group()
        if char == "\\":
            return self.parse_command()
        self.index += 1
        return Symbol(char)

    def parse_script(self) -> Expr:
        self.skip_spaces()
        if self.done:
            raise ValueError("Missing script expression.")
        if self.peek() == "{":
            return self.parse_group()
        return self.parse_atom()

    def parse_group(self) -> Expr:
        self.expect("{")
        body = self.parse_until("}")
        self.expect("}")
        return body

    def parse_command(self) -> Expr:
        self.expect("\\")
        name = self.read_command_name()
        if name == "frac":
            numerator = self.parse_required_group("numerator")
            denominator = self.parse_required_group("denominator")
            return Fraction(numerator, denominator)
        if name == "sqrt":
            return Sqrt(self.parse_required_group("radicand"))
        if name == "overline":
            return Overbar(self.parse_required_group("body"))
        if name == "underline":
            return Underbar(self.parse_required_group("body"))
        if name in {"hat", "widehat"}:
            return Hat(self.parse_required_group("body"), "hat")
        if name in {"tilde", "widetilde"}:
            return Hat(self.parse_required_group("body"), "tilde")
        if name in {"vec", "overrightarrow"}:
            return Hat(self.parse_required_group("body"), "vector")
        if name == "sum":
            return BigOperator("\u2211")
        if name == "prod":
            return BigOperator("\u220f")
        if name == "int":
            return BigOperator("\u222b")
        if name == "iint":
            return BigOperator("\u222c")
        if name == "iiint":
            return BigOperator("\u222d")
        if name in GREEK:
            return Symbol(GREEK[name])
        if name in SYMBOLS:
            return Symbol(SYMBOLS[name])
        raise ValueError(f"Unsupported LaTeX command: \\{name}")

    def parse_required_group(self, label: str) -> Expr:
        self.skip_spaces()
        if self.done or self.peek() != "{":
            raise ValueError(f"Expected {{{label}}} group.")
        return self.parse_group()

    def read_command_name(self) -> str:
        start = self.index
        while not self.done and self.peek().isalpha():
            self.index += 1
        if self.index == start and not self.done:
            self.index += 1
        name = self.source[start:self.index]
        if not name:
            raise ValueError("Empty LaTeX command.")
        return name

    def skip_spaces(self) -> None:
        while not self.done and self.peek().isspace():
            self.index += 1

    def expect(self, value: str) -> None:
        if self.done or self.source[self.index] != value:
            raise ValueError(f"Expected {value!r} at offset {self.index}.")
        self.index += 1

    def take(self) -> str:
        value = self.peek()
        self.index += 1
        return value

    def peek(self) -> str:
        return self.source[self.index]
