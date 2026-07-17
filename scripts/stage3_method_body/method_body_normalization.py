"""Deterministic Body V1 lexical normalization for isolated Stage 3B inputs.

The normalizer deliberately works on the Shimple text emitted by the Soot
extractor, but does not expose that text to the embedding model.  It keeps a
small, auditable lexical view of behaviour and removes structural identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import re
from typing import Iterable


BODY_TOKEN_BUDGET = 256
MAX_LITERAL_LENGTH = 80
MIN_LITERAL_LENGTH = 2
REPEATED_TOKEN_CAP = 2

NO_METHOD_BODY = "[NO_METHOD_BODY]"
BODY_UNAVAILABLE = "[BODY_UNAVAILABLE]"

_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_FQN = re.compile(r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+\b")
_OWNER_SIGNATURE = re.compile(r"<[^>]*>")
_STRING = re.compile(r'"(?:\\.|[^"\\])*"')
_PATH = re.compile(r"(?:[A-Za-z]:)?[/\\][^\s]*|(?:\.\.?[/\\])[^\s]*")
_URL = re.compile(r"(?i)\b(?:https?|ftp)://|\bwww\.")
_UUID = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b")
_HASH = re.compile(r"(?i)\b[0-9a-f]{16,}\b")
_TIMESTAMP = re.compile(r"\b\d{4}[-/:]\d{1,2}[-/:]\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?\b")
_PURE_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[fFdDlL]?$")

_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char",
    "class", "const", "continue", "default", "do", "double", "else", "enum",
    "extends", "final", "finally", "float", "for", "goto", "if", "implements",
    "import", "instanceof", "int", "interface", "long", "native", "new", "package",
    "private", "protected", "public", "return", "short", "static", "strictfp",
    "super", "switch", "synchronized", "this", "throw", "throws", "transient",
    "try", "void", "volatile", "while", "true", "false", "null", "var",
}
_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "is", "it",
    "of", "on", "or", "the", "to", "with", "this", "that", "then", "else",
}
_SYNTHETIC_LOCAL = re.compile(
    r"^(?:\$?(?:r|i|l|f|d|b|c|z|u|tmp|temp|stack|parameter|this)\d*|this)$",
    re.IGNORECASE,
)
_BOILERPLATE_LITERAL = re.compile(
    r"(?i)^(?:debug|trace|info|warn|error|copyright|license|generated|todo|fixme|null)$"
)
_OPERATION_TOKENS = {
    "virtualinvoke": "invoke",
    "interfaceinvoke": "invoke",
    "specialinvoke": "invoke",
    "staticinvoke": "invoke",
    "invoke": "invoke",
    "if": "branch",
    "goto": "jump",
    "return": "return",
    "throw": "throw",
    "new": "create",
    "newarray": "create",
    "newmultiarray": "create",
    "cast": "cast",
    "lengthof": "measure",
}


@dataclass(frozen=True)
class MethodBody:
    class_id: str
    method_name: str
    method_signature: str
    concrete: bool
    synthetic: bool
    body_text: str


@dataclass
class FilterCounts:
    accepted_literals: int = 0
    rejected_literals: dict[str, int] = field(default_factory=dict)
    skipped_synthetic_methods: int = 0
    skipped_nonconcrete_methods: int = 0
    unavailable_methods: int = 0

    def reject_literal(self, reason: str) -> None:
        self.rejected_literals[reason] = self.rejected_literals.get(reason, 0) + 1


@dataclass(frozen=True)
class NormalizedBody:
    body_text: str
    tokens_before_budget: tuple[str, ...]
    tokens_after_budget: tuple[str, ...]
    tokens_truncated: int
    method_count: int
    filter_counts: FilterCounts


@dataclass(frozen=True)
class _Candidate:
    token: str
    priority: int
    source_index: int


def split_identifier(value: str) -> list[str]:
    """Split Java, camelCase, PascalCase, snake_case and kebab-case names."""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
    value = re.sub(r"[_\-.$]+", " ", value)
    return [part.lower() for part in value.split() if part]


def _clean_token(value: str) -> list[str]:
    output: list[str] = []
    for piece in split_identifier(value):
        if not piece or piece in _KEYWORDS or piece in _STOPWORDS:
            continue
        if _PURE_NUMBER.fullmatch(piece) or _SYNTHETIC_LOCAL.fullmatch(piece):
            continue
        if not re.fullmatch(r"[a-z][a-z0-9]*", piece):
            continue
        if len(piece) < 2:
            continue
        output.append(piece)
    return output


def _literal_tokens(raw: str, counts: FilterCounts) -> list[str]:
    value = raw[1:-1]
    value = html.unescape(value)
    value = re.sub(r"\\([\\\"'nrtbf])", r"\1", value)
    stripped = value.strip()
    if not stripped:
        counts.reject_literal("empty")
        return []
    if len(stripped) < MIN_LITERAL_LENGTH or len(stripped) > MAX_LITERAL_LENGTH:
        counts.reject_literal("length")
        return []
    if _URL.search(stripped):
        counts.reject_literal("url")
        return []
    if _PATH.search(stripped):
        counts.reject_literal("path")
        return []
    if _UUID.search(stripped):
        counts.reject_literal("uuid")
        return []
    if _HASH.search(stripped):
        counts.reject_literal("hash")
        return []
    if _TIMESTAMP.search(stripped) or _PURE_NUMBER.fullmatch(stripped):
        counts.reject_literal("numeric_or_timestamp")
        return []
    if _BOILERPLATE_LITERAL.fullmatch(stripped):
        counts.reject_literal("boilerplate")
        return []
    tokens = [token for token in _clean_token(stripped) if len(token) >= 2]
    if not tokens:
        counts.reject_literal("no_meaningful_tokens")
        return []
    counts.accepted_literals += 1
    return tokens


def _simple_name(value: str) -> str:
    return value.rsplit(".", 1)[-1].rsplit("$", 1)[-1]


def normalize_method_body(method: MethodBody, counts: FilterCounts | None = None) -> list[str]:
    """Return ordered lexical candidates for one concrete, non-synthetic method."""
    counts = counts or FilterCounts()
    if not method.concrete:
        counts.skipped_nonconcrete_methods += 1
        return []
    if method.synthetic:
        counts.skipped_synthetic_methods += 1
        return []
    candidates: list[_Candidate] = []
    source_index = 0

    def add(value: str, priority: int) -> None:
        nonlocal source_index
        for token in _clean_token(value):
            candidates.append(_Candidate(token, priority, source_index))
            source_index += 1

    if method.method_name not in {"<init>", "<clinit>"}:
        add(method.method_name, 0)

    text = method.body_text or ""
    # Capture permitted lexical evidence before removing owner/signature text.
    for match in re.finditer(
        r"<[^>]*:\s*[^\s]+(?:\s+[^\s]+)*\s+([A-Za-z_$][A-Za-z0-9_$]*|<init>|<clinit>)\s*\(",
        text,
    ):
        if match.group(1) not in {"<init>", "<clinit>"}:
            add(match.group(1), 0)
    for match in re.finditer(r"<[^>]*:\s*[^\s]+\s+([A-Za-z_$][A-Za-z0-9_$]*)>", text):
        add(match.group(1), 1)
    for match in re.finditer(
        r"(?i)\b(?:catch|throw|new|instanceof)\s+([A-Za-z_$][A-Za-z0-9_$.]*)", text
    ):
        simple = _simple_name(match.group(1))
        if re.search(r"(?i)(?:exception|error|throwable)$", simple):
            add(simple, 1)

    for match in _STRING.finditer(text):
        for token in _literal_tokens(match.group(0), counts):
            candidates.append(_Candidate(token, 1, source_index))
            source_index += 1

    working = _STRING.sub(" ", text)
    working = _OWNER_SIGNATURE.sub(" ", working)
    working = _FQN.sub(" ", working)
    working = _PATH.sub(" ", working)
    for match in _IDENTIFIER.finditer(working):
        raw = match.group(0)
        lowered = raw.lower()
        if lowered in _OPERATION_TOKENS:
            add(_OPERATION_TOKENS[lowered], 0)
            continue
        if lowered in _KEYWORDS or _SYNTHETIC_LOCAL.fullmatch(raw):
            continue
        # Names retained by the general lexical pass must not look like
        # generated locals or JVM/type syntax.  Owner names were removed above.
        for token in _clean_token(raw):
            candidates.append(_Candidate(token, 2, source_index))
            source_index += 1

    candidates.sort(key=lambda item: (item.priority, item.source_index))
    per_method_seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        if candidate.token in per_method_seen:
            continue
        per_method_seen.add(candidate.token)
        ordered.append(candidate.token)
    return ordered


def normalize_class_bodies(methods: Iterable[MethodBody]) -> NormalizedBody:
    counts = FilterCounts()
    sorted_methods = sorted(methods, key=lambda item: (item.method_name, item.method_signature))
    candidates: list[str] = []
    for method in sorted_methods:
        candidates.extend(normalize_method_body(method, counts))

    counts_by_token: dict[str, int] = {}
    capped: list[str] = []
    for token in candidates:
        seen = counts_by_token.get(token, 0)
        if seen >= REPEATED_TOKEN_CAP:
            continue
        counts_by_token[token] = seen + 1
        capped.append(token)
    before = tuple(capped)
    after = before[:BODY_TOKEN_BUDGET]
    if after:
        body_text = " ".join(after)
    elif sorted_methods:
        body_text = BODY_UNAVAILABLE
    else:
        body_text = NO_METHOD_BODY
    return NormalizedBody(
        body_text=body_text,
        tokens_before_budget=before,
        tokens_after_budget=after,
        tokens_truncated=max(0, len(before) - len(after)),
        method_count=sum(1 for item in sorted_methods if item.concrete and not item.synthetic),
        filter_counts=counts,
    )


def compose_semantic_text(declaration: str, body_text: str) -> str:
    """Append the body marker directly after the declaration's final newline.

    This makes the bytes between ``[DECLARATION]\n`` and ``[METHOD_BODY]\n``
    exactly equal to the frozen Stage 3A semantic_text.
    """
    declaration = declaration.replace("\r\n", "\n").replace("\r", "\n")
    if not declaration.endswith("\n"):
        raise ValueError("declaration semantic_text must end with a newline")
    return f"[DECLARATION]\n{declaration}[METHOD_BODY]\n{body_text}\n"


def extract_declaration_section(semantic_text: str) -> str:
    marker = "[DECLARATION]\n"
    body_marker = "[METHOD_BODY]\n"
    if not semantic_text.startswith(marker) or body_marker not in semantic_text:
        raise ValueError("missing Body V1 section markers")
    start = len(marker)
    end = semantic_text.index(body_marker, start)
    return semantic_text[start:end]
