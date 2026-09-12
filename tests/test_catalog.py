import pytest
from pydantic import ValidationError

from meridian.catalog import ServiceEntry, load_catalog, validate_consistency


def _entry(name: str, **overrides) -> ServiceEntry:
    defaults = dict(
        name=name,
        tier=1,
        owner="test-team",
        description="A test service.",
        depends_on=[],
        depended_on_by=[],
        slo={"availability": 99.9, "latency_p99_ms": 200},
        runbooks=[],
        blast_radius="Minimal.",
    )
    defaults.update(overrides)
    return ServiceEntry.model_validate(defaults)


def test_load_catalog_reads_every_service_in_the_spec_table():
    # The spec's per-layer table sums to 41 named services, though prose
    # elsewhere calls it "~45" -- this pins the count to what's actually named.
    catalog = load_catalog()
    assert len(catalog) == 41
    assert "postgres-primary" in catalog
    assert "checkout-api" in catalog


def test_checkout_api_matches_spec_example():
    catalog = load_catalog()
    checkout = catalog["checkout-api"]

    assert checkout.tier == 1
    assert checkout.owner == "payments-platform"
    assert checkout.oncall_rotation == "payments-oncall"
    assert checkout.depends_on == [
        "auth-service",
        "postgres-primary",
        "stripe-gateway",
        "inventory-service",
        "pricing-engine",
    ]
    assert set(checkout.depended_on_by) == {"web-frontend", "mobile-api"}
    assert checkout.slo.availability == 99.95
    assert checkout.slo.latency_p99_ms == 400


def test_real_catalog_has_no_consistency_errors():
    catalog = load_catalog()
    assert validate_consistency(catalog) == []


def test_third_party_services_have_no_oncall_rotation():
    catalog = load_catalog()
    for name in ["stripe-gateway", "twilio-sms", "sendgrid-email", "s3-storage", "cloudflare-cdn"]:
        assert catalog[name].tier == "external"
        assert catalog[name].oncall_rotation is None


def test_rejects_non_kebab_case_name():
    with pytest.raises(ValidationError):
        _entry("Checkout_API")


def test_validate_consistency_catches_one_sided_depends_on():
    catalog = {
        "a": _entry("a", depends_on=["b"], depended_on_by=[]),
        "b": _entry("b", depends_on=[], depended_on_by=[]),
    }

    errors = validate_consistency(catalog)

    assert len(errors) == 1
    assert "a" in errors[0] and "b" in errors[0]


def test_validate_consistency_catches_one_sided_depended_on_by():
    catalog = {
        "a": _entry("a", depends_on=[], depended_on_by=[]),
        "b": _entry("b", depends_on=[], depended_on_by=["a"]),
    }

    errors = validate_consistency(catalog)

    assert len(errors) == 1
    assert "a" in errors[0] and "b" in errors[0]


def test_validate_consistency_catches_reference_to_unknown_service():
    catalog = {
        "a": _entry("a", depends_on=["ghost-service"], depended_on_by=[]),
    }

    errors = validate_consistency(catalog)

    assert len(errors) == 1
    assert "ghost-service" in errors[0]


def test_validate_consistency_passes_for_correctly_paired_edges():
    catalog = {
        "a": _entry("a", depends_on=["b"], depended_on_by=[]),
        "b": _entry("b", depends_on=[], depended_on_by=["a"]),
    }

    assert validate_consistency(catalog) == []
