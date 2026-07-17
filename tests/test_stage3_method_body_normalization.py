from __future__ import annotations

from scripts.stage3_method_body.method_body_normalization import (
    EMPTY_BODY,
    MethodBody,
    compose_semantic_text,
    extract_declaration_section,
    normalize_class_bodies,
    normalize_method_body,
    split_identifier,
)


def method(name: str, text: str, *, concrete: bool = True, synthetic: bool = False) -> MethodBody:
    return MethodBody("com.example.Sample", name, f"<com.example.Sample: void {name}()>", concrete, synthetic, text)


def test_identifier_splitting_handles_camel_pascal_acronym_and_snake_case() -> None:
    assert split_identifier("getXMLReader") == ["get", "xml", "reader"]
    assert split_identifier("PaymentStatus") == ["payment", "status"]
    assert split_identifier("save_order-status") == ["save", "order", "status"]


def test_invocation_owner_and_type_edges_are_removed() -> None:
    body = (
        "r0 = virtualinvoke r1.<com.shop.payment.PaymentService: java.lang.String "
        "authorize(java.lang.String)>(r2); r3 = (java.lang.String) r0; "
        "r4 = new com.shop.payment.PaymentService;"
    )
    normalized = normalize_class_bodies([method("authorizePayment", body)])
    assert "authorize" in normalized.tokens_after_budget
    assert "payment" in normalized.tokens_after_budget
    assert "service" not in normalized.tokens_after_budget
    assert not any("com" in token or "java" in token for token in normalized.tokens_after_budget)


def test_field_exception_and_operation_evidence_are_retained() -> None:
    body = (
        "r0 = r1.<com.shop.Order: java.lang.String paymentStatus>; "
        "if r0 == null goto label1; throw new java.io.IOException; label1: return;"
    )
    normalized = normalize_class_bodies([method("validateOrder", body)])
    assert "payment" in normalized.tokens_after_budget
    assert "status" in normalized.tokens_after_budget
    assert "io" in normalized.tokens_after_budget
    assert "exception" in normalized.tokens_after_budget
    assert "branch" in normalized.tokens_after_budget
    assert "label1" not in normalized.tokens_after_budget


def test_synthetic_locals_and_generic_accessors_are_removed_but_object_word_remains() -> None:
    body = "$r0 = virtualinvoke $r1.<x.Y: void setValue(java.lang.String)>($r2);"
    normalized = normalize_class_bodies([method("getCustomer", body), method("toString", body)])
    assert "customer" in normalized.tokens_after_budget
    assert "value" in normalized.tokens_after_budget
    assert "get" not in normalized.tokens_after_budget
    assert "set" not in normalized.tokens_after_budget
    assert "tostring" not in normalized.tokens_after_budget
    assert "r0" not in normalized.tokens_after_budget


def test_string_literals_accept_domain_words_and_reject_sensitive_or_boilerplate_values() -> None:
    body = (
        'r0 = "validate cart"; r1 = "https://example.com"; r2 = "/Users/local/file"; '
        'r3 = "550e8400-e29b-41d4-a716-446655440000"; r4 = "2024-01-02"; '
        'r5 = "debug"; r6 = "AQIDBAUGBwgJCgsMDQ4PEA==";'
    )
    normalized = normalize_class_bodies([method("parseCart", body)])
    assert "validate" in normalized.tokens_after_budget
    assert "cart" in normalized.tokens_after_budget
    assert all(token not in normalized.tokens_after_budget for token in ("https", "users", "local", "debug"))
    reasons = {item["decision"] for item in normalized.literal_audit}
    assert {"url", "path", "uuid", "numeric_or_timestamp", "boilerplate", "encoded_or_binary"} <= reasons


def test_empty_abstract_constructor_and_static_initializer_contract() -> None:
    assert normalize_class_bodies([]).body_text == EMPTY_BODY
    assert normalize_class_bodies([method("abstractMethod", "", concrete=False)]).body_text == EMPTY_BODY
    normalized = normalize_class_bodies([
        method("<init>", "r0 = new java.lang.StringBuilder;"),
        method("<clinit>", "r0 = staticinvoke <x.Y: void initialize()>()"),
    ])
    assert normalized.body_text != EMPTY_BODY
    assert "initialize" in normalized.tokens_after_budget


def test_repeated_tokens_are_capped_and_order_is_deterministic() -> None:
    methods = [
        method("zetaAction", "r0 = virtualinvoke r1.<x.Y: void saveOrder()>()" * 10),
        method("alphaAction", "r0 = virtualinvoke r1.<x.Y: void validateCart()>()" * 10),
    ]
    first = normalize_class_bodies(methods)
    second = normalize_class_bodies(list(reversed(methods)))
    assert first.body_text == second.body_text
    assert all(first.tokens_after_budget.count(token) <= 2 for token in first.tokens_after_budget)


def test_section_delimiters_preserve_declaration_byte_for_byte() -> None:
    declaration = "public class Sample {\n    void validate();\n}\n"
    semantic = compose_semantic_text(declaration, "validate cart")
    assert extract_declaration_section(semantic) == declaration
    assert semantic == (
        "[DECLARATION]\npublic class Sample {\n    void validate();\n}\n"
        "[METHOD_BODY]\nvalidate cart\n"
    )


def test_raw_switch_syntax_is_never_emitted_from_multiline_field_context() -> None:
    body = "<example.C: short type>\n$i1 = (int) $s0\ntableswitch($i1) { case 1: goto return 1; }"
    normalized = normalize_class_bodies([method("toString", body)])
    assert "tableswitch" not in normalized.body_text
    assert "lookupswitch" not in normalized.body_text
