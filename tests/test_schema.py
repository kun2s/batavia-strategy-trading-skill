import json
from pathlib import Path
import unittest

import jsonschema
from jsonschema import ValidationError

from batavia.regime import Evidence, Signals, build_spec


class SchemaTests(unittest.TestCase):
    def source(self):
        return {"name": "cmc", "observed_at": "2026-06-20T09:30:00Z"}

    def validate(self, receipt, schema):
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker()
        )
        validator.validate(receipt)

    def test_v02_receipt_validates(self):
        schema = json.loads(Path("schema/regime_strategy.schema.json").read_text())
        receipt = build_spec(
            "BNB", Signals(60, 0.7, "normal", 0.1),
            evidence=Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        self.validate(receipt, schema)

    def test_nested_unknown_field_is_rejected(self):
        schema = json.loads(Path("schema/regime_strategy.schema.json").read_text())
        receipt = build_spec(
            "BNB", Signals(60, 0.7, "normal", 0.1),
            evidence=Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        receipt["active_strategy"]["unexpected"] = True
        with self.assertRaises(ValidationError):
            jsonschema.validate(receipt, schema)

    def test_incomplete_volatility_sizing_is_rejected(self):
        schema = json.loads(Path("schema/regime_strategy.schema.json").read_text())
        receipt = build_spec(
            "BNB", Signals(60, 0.7, "normal", 0.1),
            evidence=Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        del receipt["active_strategy"]["sizing"]["reference_atr_pct"]
        with self.assertRaises(ValidationError):
            jsonschema.validate(receipt, schema)


if __name__ == "__main__":
    unittest.main()
