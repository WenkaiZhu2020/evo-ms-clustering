"""Deterministic Body V1 lexical normalization for Stage 3B inputs.

The Soot extractor supplies Shimple text as a parsing source.  This module
never exposes raw Shimple syntax, owner identities, type signatures, or
temporary locals to the semantic text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import html
import re
import unicodedata
from typing import Iterable


BODY_TOKEN_BUDGET = 256
MAX_LITERAL_LENGTH = 80
MIN_LITERAL_LENGTH = 2
REPEATED_TOKEN_CAP = 2
EMPTY_BODY = "<EMPTY>"

_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")
_FQN = re.compile(r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:\.[A-Za-z_$][A-Za-z0-9_$]*)+\b")
_OWNER_SIGNATURE = re.compile(r"<[^>]*>")
_STRING = re.compile(r'"(?:\\.|[^"\\])*"')
_PATH = re.compile(r"(?:[A-Za-z]:)?[/\\][^\s]*|(?:\.\.?[/\\])[^\s]*")
_URL = re.compile(r"(?i)\b(?:https?|ftp)://|\bwww\.")
_NAMESPACE_URI = re.compile(r"(?i)\b(?:urn:|xmlns(?::[A-Za-z0-9_-]+)?\s*=)")
_UUID = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b")
_HASH = re.compile(r"(?i)\b[0-9a-f]{16,}\b")
_TIMESTAMP = re.compile(r"\b\d{4}[-/:]\d{1,2}[-/:]\d{1,2}(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?\b")
_PURE_NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[fFdDlL]?$")
_ENCODED = re.compile(r"^[A-Za-z0-9+/=_-]{24,}$")
_FORMAT_ONLY = re.compile(r"^[%{}$#@:_.,;\-+*/\\\s\d]+$")
_JIMPLE_LABEL = re.compile(r"\b(?:label|target|loc)\d+\b(?::)?", re.IGNORECASE)

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
    "a", "an", "and", "as", "at", "be", "by", "do", "for", "from", "in", "is",
    "it", "of", "on", "or", "the", "to", "with", "this", "that", "then", "else",
}
_GENERIC_METHODS = {"tostring", "hashcode", "equals", "init", "clinit", "main", "run"}
_ACCESSORS = {"get", "set", "is"}
_SYNTHETIC_LOCAL = re.compile(
    r"^(?:\$?(?:r|i|l|f|d|b|c|z|u|tmp|temp|stack|parameter|arg|local)\d*|this)$",
    re.IGNORECASE,
)
_BOILERPLATE_LITERAL = re.compile(
    r"(?i)^(?:debug|trace|info|warn|warning|error|copyright|license|generated|todo|fixme|null)$"
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
_RAW_JIMPLE_TOKENS = {
    "dynamicinvoke", "tableswitch", "lookupswitch", "identity", "phi", "nop", "caughtexception",
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
    raw_candidate_count: int = 0
    accepted_invoked_method_tokens: int = 0
    accepted_field_tokens: int = 0
    accepted_local_tokens: int = 0
    accepted_exception_tokens: int = 0
    accepted_operation_tokens: int = 0
    accepted_string_tokens: int = 0
    accepted_literals: int = 0
    rejected_tokens: dict[str, int] = field(default_factory=dict)
    rejected_literals: dict[str, int] = field(default_factory=dict)
    skipped_synthetic_methods: int = 0
    skipped_nonconcrete_methods: int = 0

    def reject(self, reason: str) -> None:
        self.rejected_tokens[reason] = self.rejected_tokens.get(reason, 0) + 1

    def reject_literal(self, reason: str) -> None:
        self.rejected_literals[reason] = self.rejected_literals.get(reason, 0) + 1
        self.reject(f"literal_{reason}")


@dataclass(frozen=True)
class NormalizedBody:
    body_text: str
    tokens_before_budget: tuple[str, ...]
    tokens_after_budget: tuple[str, ...]
    tokens_truncated: int
    method_count: int
    filter_counts: FilterCounts
    literal_audit: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class _Candidate:
    token: str
    priority: int
    source_index: int


def split_identifier(value: str) -> list[str]:
    """Normalize Unicode and split camel, Pascal, acronym, snake, and kebab names."""
    value = unicodedata.normalize("NFKC", value).replace("$", " ")
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
    value = re.sub(r"[_\-.]+", " ", value)
    return [part.lower() for part in value.split() if part]


def _clean_identifier(value: str, *, accessor_policy: bool = True) -> list[str]:
    parts = split_identifier(value)
    if not parts:
        return []
    if parts[0] in _GENERIC_METHODS:
        return []
    if accessor_policy and parts[0] in _ACCESSORS:
        parts = parts[1:]
    output: list[str] = []
    for part in parts:
        if part in _KEYWORDS or part in _STOPWORDS:
            continue
        if _PURE_NUMBER.fullmatch(part) or _SYNTHETIC_LOCAL.fullmatch(part):
            continue
        if not re.fullmatch(r"[a-z][a-z0-9]*", part):
            continue
        if len(part) < 2:
            continue
        output.append(part)
    return output


def _simple_name(value: str) -> str:
    return value.rsplit(".", 1)[-1].rsplit("$", 1)[-1]


def _literal_tokens(raw: str, counts: FilterCounts, audit: list[dict[str, str]]) -> list[str]:
    value = html.unescape(raw[1:-1])
    for escaped, replacement in (
        ("\\n", " "), ("\\r", " "), ("\\t", " "), ("\\b", " "),
        ("\\f", " "), ("\\\"", '"'), ("\\'", "'"), ("\\\\", "\\"),
    ):
        value = value.replace(escaped, replacement)
    stripped = unicodedata.normalize("NFKC", value).strip()
    reason = "accepted"
    if not stripped:
        reason = "empty"
    elif len(stripped) < MIN_LITERAL_LENGTH or len(stripped) > MAX_LITERAL_LENGTH:
        reason = "length"
    elif _URL.search(stripped):
        reason = "url"
    elif _NAMESPACE_URI.search(stripped):
        reason = "namespace_uri"
    elif _PATH.search(stripped):
        reason = "path"
    elif _UUID.search(stripped):
        reason = "uuid"
    elif _HASH.search(stripped):
        reason = "hash"
    elif _TIMESTAMP.search(stripped) or _PURE_NUMBER.fullmatch(stripped):
        reason = "numeric_or_timestamp"
    elif _ENCODED.fullmatch(stripped) and not re.search(r"[^A-Za-z0-9+/=_-]", stripped):
        reason = "encoded_or_binary"
    elif _FORMAT_ONLY.fullmatch(stripped):
        reason = "format_only"
    elif _BOILERPLATE_LITERAL.fullmatch(stripped):
        reason = "boilerplate"
    tokens = [] if reason != "accepted" else _clean_identifier(stripped, accessor_policy=False)
    if reason == "accepted" and not tokens:
        reason = "no_meaningful_tokens"
    if reason != "accepted":
        counts.reject_literal(reason)
    else:
        counts.accepted_literals += 1
        counts.accepted_string_tokens += len(tokens)
    # Keep normalized previews only; never record the original literal value.
    audit.append({"decision": reason, "normalized_tokens": " ".join(tokens)})
    return tokens


def normalize_method_body(
    method: MethodBody,
    counts: FilterCounts | None = None,
    literal_audit: list[dict[str, str]] | None = None,
) -> list[str]:
    """Return deterministic lexical candidates for one method."""
    counts = counts or FilterCounts()
    literal_audit = literal_audit if literal_audit is not None else []
    if not method.concrete:
        counts.skipped_nonconcrete_methods += 1
        return []
    if method.synthetic:
        counts.skipped_synthetic_methods += 1
        return []
    candidates: list[_Candidate] = []
    source_index = 0

    def add(value: str, priority: int, feature: str) -> None:
        nonlocal source_index
        counts.raw_candidate_count += 1
        tokens = _clean_identifier(value, accessor_policy=True)
        if not tokens:
            counts.reject("boilerplate_or_invalid_identifier")
        for token in tokens:
            candidates.append(_Candidate(token, priority, source_index))
            source_index += 1
            if feature == "invoked_method":
                counts.accepted_invoked_method_tokens += 1
            elif feature == "field":
                counts.accepted_field_tokens += 1
            elif feature == "local":
                counts.accepted_local_tokens += 1
            elif feature == "exception":
                counts.accepted_exception_tokens += 1
            elif feature == "operation":
                counts.accepted_operation_tokens += 1

    if method.method_name not in {"<init>", "<clinit>"}:
        add(method.method_name, 0, "invoked_method")

    text = unicodedata.normalize("NFKC", method.body_text or "")
    # Capture permitted simple names before removing owner/signature material.
    for match in re.finditer(
        r"<[^>\n]*:\s*[^\s\n]+(?:\s+[^\s\n]+)*\s+([A-Za-z_$][A-Za-z0-9_$]*|<init>|<clinit>)\s*\(",
        text,
    ):
        name = match.group(1)
        if name not in {"<init>", "<clinit>"}:
            add(name, 0, "invoked_method")
    for match in re.finditer(r"<[^>\n]*:\s*[^\s\n]+\s+([A-Za-z_$][A-Za-z0-9_$]*)>", text):
        add(match.group(1), 1, "field")
    for match in re.finditer(
        r"(?i)\b(?:catch|throw|new|instanceof)\s+([A-Za-z_$][A-Za-z0-9_$.]*)", text
    ):
        simple = _simple_name(match.group(1))
        if re.search(r"(?i)(?:exception|error|throwable)$", simple):
            add(simple, 1, "exception")
    for match in re.finditer(r"(?i)\b(?:new|instanceof)\s+([A-Za-z_$][A-Za-z0-9_$.]*)", text):
        simple = _simple_name(match.group(1))
        if re.search(r"(?i)(?:exception|error|throwable)$", simple):
            add(simple, 1, "exception")

    for match in _STRING.finditer(text):
        for token in _literal_tokens(match.group(0), counts, literal_audit):
            candidates.append(_Candidate(token, 1, source_index))
            source_index += 1

    # Remove string values, owner signatures, FQNs, and type-context names
    # before the general pass.  This is the type-edge and owner-leakage guard.
    working = _STRING.sub(" ", text)
    working = _OWNER_SIGNATURE.sub(" ", working)
    working = re.sub(
        r"\b(new|instanceof|cast)\s+[A-Za-z_$][A-Za-z0-9_$.]*", r"\1 ", working
    )
    working = _FQN.sub(" ", working)
    working = _PATH.sub(" ", working)
    working = _JIMPLE_LABEL.sub(" ", working)
    for match in _IDENTIFIER.finditer(working):
        raw = match.group(0)
        lowered = raw.lower()
        if lowered in _OPERATION_TOKENS:
            add(_OPERATION_TOKENS[lowered], 0, "operation")
            continue
        if lowered in _RAW_JIMPLE_TOKENS:
            counts.reject("raw_jimple_syntax")
            continue
        if lowered in _KEYWORDS:
            counts.reject("java_keyword")
            continue
        if _SYNTHETIC_LOCAL.fullmatch(raw):
            counts.reject("synthetic_local")
            continue
        if raw[:1].isupper():
            counts.reject("type_like_identifier")
            continue
        add(raw, 2, "local")

    candidates.sort(key=lambda item: (item.priority, item.source_index))
    per_method_seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        if candidate.token in _RAW_JIMPLE_TOKENS:
            counts.reject("raw_jimple_syntax")
            continue
        if candidate.token in per_method_seen:
            counts.reject("duplicate_within_method")
            continue
        per_method_seen.add(candidate.token)
        ordered.append(candidate.token)
    return ordered


def normalize_class_bodies(methods: Iterable[MethodBody]) -> NormalizedBody:
    counts = FilterCounts()
    literal_audit: list[dict[str, str]] = []
    sorted_methods = sorted(methods, key=lambda item: (item.method_name, item.method_signature))
    candidates: list[str] = []
    for method in sorted_methods:
        candidates.extend(normalize_method_body(method, counts, literal_audit))

    counts_by_token: dict[str, int] = {}
    capped: list[str] = []
    for token in candidates:
        seen = counts_by_token.get(token, 0)
        if seen >= REPEATED_TOKEN_CAP:
            counts.reject("repeated_token_cap")
            continue
        counts_by_token[token] = seen + 1
        capped.append(token)
    before = tuple(capped)
    after = before[:BODY_TOKEN_BUDGET]
    body_text = " ".join(after) if after else EMPTY_BODY
    return NormalizedBody(
        body_text=body_text,
        tokens_before_budget=before,
        tokens_after_budget=after,
        tokens_truncated=max(0, len(before) - len(after)),
        method_count=sum(1 for item in sorted_methods if item.concrete and not item.synthetic),
        filter_counts=counts,
        literal_audit=tuple(literal_audit),
    )


def compose_semantic_text(declaration: str, body_text: str) -> str:
    """Append the body marker without changing any declaration bytes."""
    if "\r" in declaration or not declaration.endswith("\n"):
        raise ValueError("declaration semantic_text must be LF-terminated")
    if "[DECLARATION]" in declaration or "[METHOD_BODY]" in declaration:
        raise ValueError("Stage 3A declaration contains reserved Body V1 markers")
    return f"[DECLARATION]\n{declaration}[METHOD_BODY]\n{body_text}\n"


def extract_declaration_section(semantic_text: str) -> str:
    marker = "[DECLARATION]\n"
    body_marker = "[METHOD_BODY]\n"
    if not semantic_text.startswith(marker) or body_marker not in semantic_text:
        raise ValueError("missing Body V1 section markers")
    start = len(marker)
    end = semantic_text.index(body_marker, start)
    return semantic_text[start:end]
