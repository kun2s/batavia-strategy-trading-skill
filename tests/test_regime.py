import json
from pathlib import Path
import unittest

from batavia.regime import (
    ACTIVE, EUPHORIA, INSUFFICIENT_DATA, RANGING, RISK_OFF, STAND_ASIDE,
    TRENDING_UP, Evidence, Signals, build_spec, classify,
)


class RegimeTests(unittest.TestCase):
    def source(self, observed_at="2026-06-20T09:30:00Z"):
        return {"name": "cmc", "observed_at": observed_at}

    def test_boundaries(self):
        self.assertEqual(classify(Signals(80, 0.8, "normal", 0.5))[0], EUPHORIA)
        self.assertEqual(classify(Signals(20, 0.8, "normal", 0.0))[0], RISK_OFF)
        self.assertEqual(classify(Signals(50, 0.5, "normal", 0.0))[0], TRENDING_UP)
        self.assertEqual(classify(Signals(50, 0.0, "normal", 0.0))[0], RANGING)

    def test_active_requires_three_confirmations(self):
        signals = Signals(60, 0.8, "normal", 0.1)
        evidence = Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),))
        waiting = build_spec("BNB", signals, evidence=evidence,
                             as_of="2026-06-20T10:00:00Z", confirmation_count=2)
        active = build_spec("BNB", signals, evidence=evidence,
                            as_of="2026-06-20T10:00:00Z", confirmation_count=3)
        self.assertEqual(waiting["decision_status"], STAND_ASIDE)
        self.assertEqual(active["decision_status"], ACTIVE)

    def test_missing_and_stale_evidence_abstains(self):
        missing = build_spec("BNB", Signals(), as_of="2026-06-20T10:00:00Z")
        stale = build_spec("BNB", Signals(60, 0.8, "normal", None),
                           evidence=Evidence(1839, "2026-06-20T05:00:00Z",
                                             (self.source("2026-06-20T05:00:00Z"),)),
                           as_of="2026-06-20T10:00:00Z", confirmation_count=3)
        self.assertEqual(missing["decision_status"], INSUFFICIENT_DATA)
        self.assertEqual(stale["decision_status"], INSUFFICIENT_DATA)

    def test_future_evidence_abstains(self):
        receipt = build_spec(
            "BNB", Signals(60, 0.8, "normal", 0.1),
            evidence=Evidence(1839, "2026-06-20T11:00:00Z",
                              (self.source("2026-06-20T11:00:00Z"),)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        self.assertEqual(receipt["decision_status"], INSUFFICIENT_DATA)
        self.assertIn("observed_at_not_in_future", receipt["evidence"]["missing_inputs"])

    def test_missing_assessment_time_cannot_be_active(self):
        receipt = build_spec(
            "BNB", Signals(60, 0.8, "normal", 0.1),
            evidence=Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),)),
            confirmation_count=3,
        )
        self.assertEqual(receipt["decision_status"], INSUFFICIENT_DATA)
        self.assertIn("as_of", receipt["evidence"]["missing_inputs"])

    def test_missing_source_observation_time_cannot_be_active(self):
        receipt = build_spec(
            "BNB", Signals(60, 0.8, "normal", 0.1),
            evidence=Evidence(1839, "2026-06-20T09:30:00Z", ({"name": "cmc"},)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        self.assertEqual(receipt["decision_status"], INSUFFICIENT_DATA)
        self.assertIn("source_observed_at", receipt["evidence"]["missing_inputs"])
        self.assertIsNone(receipt["evidence"]["sources"][0]["observed_at"])

    def test_receipts_do_not_share_mutable_playbook_state(self):
        signals = Signals(60, 0.8, "normal", 0.1)
        evidence = Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),))
        first = build_spec("BNB", signals, evidence=evidence,
                           as_of="2026-06-20T10:00:00Z", confirmation_count=3)
        first["regime_playbook"][TRENDING_UP]["entry"]["rule"] = "changed"
        second = build_spec("BNB", signals, evidence=evidence,
                            as_of="2026-06-20T10:00:00Z", confirmation_count=3)
        self.assertNotEqual(second["regime_playbook"][TRENDING_UP]["entry"]["rule"], "changed")

    def test_evidence_timestamp_changes_hash(self):
        signals = Signals(60, 0.8, "normal", 0.1)
        first = build_spec(
            "BNB", signals,
            evidence=Evidence(1839, "2026-06-20T09:00:00Z",
                              (self.source("2026-06-20T09:00:00Z"),)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        second = build_spec(
            "BNB", signals,
            evidence=Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        self.assertNotEqual(first["evidence"]["hash_sha256"], second["evidence"]["hash_sha256"])

    def test_agent_hub_contract_is_emitted(self):
        receipt = build_spec(
            "BNB", Signals(60, 0.8, "normal", 0.1),
            evidence=Evidence(1839, "2026-06-20T09:30:00Z", (self.source(),)),
            as_of="2026-06-20T10:00:00Z", confirmation_count=3,
        )
        self.assertEqual(receipt["agent_hub"]["skill"], "batavia-regime-compiler")
        self.assertIn("mcp", receipt["agent_hub"]["surfaces"])
        self.assertIn("get_crypto_technical_analysis", receipt["agent_hub"]["required_mcp_tools"])
        self.assertIn("x402", receipt["agent_hub"]["x402_policy"])

    def test_invalid_signal_is_rejected_before_json_generation(self):
        with self.assertRaises(ValueError):
            build_spec("BNB", Signals(101, 0.8, "normal", 0.1))

    def test_golden_fixture_is_deterministic(self):
        fixture = json.loads((Path(__file__).parent / "fixtures/cmc_evidence.json").read_text())
        signals = Signals(**fixture["signals"])
        evidence = Evidence(fixture["cmc_id"], fixture["observed_at"], tuple(fixture["sources"]))
        first = build_spec(fixture["symbol"], signals, evidence=evidence,
                           as_of=fixture["as_of"], confirmation_count=fixture["confirmation_count"])
        self.assertEqual(first["evidence"]["hash_sha256"], fixture["expected_hash"])
        expected = json.loads((Path(__file__).parents[1] / "examples/bnb_active.json").read_text())
        self.assertEqual(first, expected)
        self.assertEqual(first["decision_status"], ACTIVE)


if __name__ == "__main__":
    unittest.main()
