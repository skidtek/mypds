import pytest
from pydantic import ValidationError

from mypds.landing.schema import LandingLayout, default_layout, migrate


def test_default_is_valid() -> None:
    doc = default_layout().dump()
    assert doc["schema"] == "mypds.landing-layout"
    assert LandingLayout.model_validate(doc).dump() == doc


def _doc(**widget):  # noqa: ANN003, ANN202
    base = {"id": "w_a", "type": "weather", "config": {}, "placement": {}}
    base.update(widget)
    return {"schema": "mypds.landing-layout", "version": 1, "widgets": [base]}


def test_rejects_overflow() -> None:
    with pytest.raises(ValidationError):
        LandingLayout.model_validate(_doc(placement={"desktop": {"x": 10, "y": 0, "w": 4, "h": 2}}))
    with pytest.raises(ValidationError):
        LandingLayout.model_validate(_doc(placement={"tablet": {"x": 6, "y": 0, "w": 4, "h": 2}}))


def test_rejects_unknown_config_and_type() -> None:
    with pytest.raises(ValidationError):
        LandingLayout.model_validate(_doc(config={"url": "http://evil"}))
    with pytest.raises(ValidationError):
        LandingLayout.model_validate(_doc(type="iframe"))


def test_rejects_duplicate_ids() -> None:
    d = _doc()
    d["widgets"].append(dict(d["widgets"][0]))
    with pytest.raises(ValidationError):
        LandingLayout.model_validate(d)


def test_mobile_order_cleaned() -> None:
    d = _doc()
    d["mobile"] = {"mode": "custom", "order": ["w_a", "w_ghost", "w_a"]}
    assert LandingLayout.model_validate(d).mobile.order == ["w_a"]


def test_unknown_version() -> None:
    with pytest.raises(ValueError):
        migrate({"version": 99})
