"""Mise en forme commune à l'éditeur visuel et aux exports de paroles."""

from html import escape, unescape
from html.parser import HTMLParser
import re
from typing import NamedTuple


class Fragment(NamedTuple):
    text: str
    bold: bool = False
    underline: bool = False


def formatted_lines(section: str) -> list[list[Fragment]]:
    section = re.sub(r"(?m)^ {0,3}#{1,6}\s+", "", section)
    section = re.sub(r"\[([^\]]*)\]\([^)]+\)", r"\1", section)
    section = "\n".join(line.rstrip() for line in section.splitlines()).strip()
    fragments = []
    position = 0
    for match in re.finditer(r"(\*\*|__)(\S(?:.*?\S)?)\1", section, re.DOTALL):
        fragments.extend(((section[position:match.start()], False), (match[2], True)))
        position = match.end()
    fragments.append((section[position:], False))
    lines = [[]]
    underline = False
    for text, bold in fragments:
        # Comme auparavant, l'italique est converti en texte simple.
        for marker in (r"\*", "_"):
            text = re.sub(marker + r"(\S(?:.*?\S)?)" + marker, r"\1", text)
        for part in re.split(r"(</?u>)", text, flags=re.IGNORECASE):
            if part.lower() in ("<u>", "</u>"):
                underline = part.lower() == "<u>"
                continue
            for index, line in enumerate(part.split("\n")):
                if index:
                    lines.append([])
                if line:
                    lines[-1].append(Fragment(unescape(line), bold, underline))
    return lines


def fragment_html(fragment: Fragment, *, force_bold: bool = False) -> str:
    result = escape(fragment.text)
    if fragment.underline:
        result = f"<u>{result}</u>"
    if fragment.bold or force_bold:
        result = f"<b>{result}</b>"
    return result


def lyrics_html(section: str) -> str:
    return "<br>".join("".join(fragment_html(fragment) for fragment in line)
                      for line in formatted_lines(section))


class _EditorHTML(HTMLParser):
    """Ne conserve que le texte, les retours à la ligne, le gras et le soulignement."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.runs: list[Fragment] = []
        self.bold = 0
        self.underline = 0
        self.ignored = 0

    def append(self, text):
        if self.ignored or not text:
            return
        fragment = Fragment(text.replace("\xa0", " "), bool(self.bold), bool(self.underline))
        if self.runs and self.runs[-1][1:] == fragment[1:]:
            self.runs[-1] = self.runs[-1]._replace(text=self.runs[-1].text + fragment.text)
        else:
            self.runs.append(fragment)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignored += 1
        elif not self.ignored:
            if tag in ("b", "strong"):
                self.bold += 1
            elif tag == "u":
                self.underline += 1
            elif tag == "br":
                self.append("\n")
            elif tag in ("div", "p") and self.runs and not self.runs[-1].text.endswith("\n"):
                self.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignored = max(0, self.ignored - 1)
        elif not self.ignored:
            if tag in ("b", "strong"):
                self.bold = max(0, self.bold - 1)
            elif tag == "u":
                self.underline = max(0, self.underline - 1)
            elif tag in ("div", "p"):
                self.append("\n")

    def handle_data(self, data):
        self.append(data)


def editor_html_to_markdown(value: str) -> str:
    parser = _EditorHTML()
    parser.feed(value)
    parser.close()
    result = []
    for text, bold, underline in parser.runs:
        for index, line in enumerate(text.split("\n")):
            if index:
                result.append("\n")
            # Les caractères de syntaxe tapés par l'utilisateur restent du texte.
            line = re.sub(r"[*_#\[\]`\\]", lambda match: f"&#{ord(match[0])};", escape(line, quote=False))
            if line.strip() == "---":
                line = line.replace("-", "&#45;")
            if not line.strip():
                result.append(line)
                continue
            leading = line[:len(line) - len(line.lstrip())]
            trailing = line[len(line.rstrip()):]
            content = line.strip()
            if underline:
                content = f"<u>{content}</u>"
            if bold:
                content = f"**{content}**"
            result.append(leading + content + trailing)
    return "".join(result).strip()
