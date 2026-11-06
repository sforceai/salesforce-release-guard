"""Small Apex lexical masker. Not an Apex parser or data-flow engine."""
import re


TOKEN = re.compile(r"//[^\n]*|/\*[\s\S]*?\*/|'(?:\\[\s\S]|[^'\\])*'")


def mask(source, strings=True):
    def replace(match):
        value = match.group()
        if value.startswith("'") and not strings:
            return value
        return ''.join('\n' if c == '\n' else ' ' for c in value)
    return TOKEN.sub(replace, source)


def line_at(source, position):
    return source.count('\n', 0, position) + 1


def safe_excerpt(source, line):
    """Never emit Apex string literal values, including potential credentials."""
    redacted = TOKEN.sub(lambda m: "'[redacted]'" if m.group().startswith("'") else
                         ''.join('\n' if c == '\n' else ' ' for c in m.group()), source)
    lines = redacted.splitlines()
    return lines[line - 1].strip()[:240] if 0 < line <= len(lines) else ''
