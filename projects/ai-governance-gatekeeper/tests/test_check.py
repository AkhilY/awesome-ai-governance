import json
import unittest
from pathlib import Path
from governance.check import evaluate

ROOT=Path(__file__).resolve().parents[1]
class GovernanceChecks(unittest.TestCase):
    def test_complete_manifest_passes(self):
        data=json.loads((ROOT/"examples/senior_assistant.json").read_text())
        self.assertTrue(all(c["status"]=="pass" for c in evaluate(data)))
    def test_incomplete_manifest_fails(self):
        data=json.loads((ROOT/"examples/incomplete_assistant.json").read_text())
        failed={c["id"] for c in evaluate(data) if c["status"]=="fail"}
        self.assertIn("GOV-OWNER",failed)
        self.assertIn("MANAGE-HUMAN",failed)
    def test_high_risk_requires_approval(self):
        data=json.loads((ROOT/"examples/senior_assistant.json").read_text())
        data["approval_reference"]=""
        self.assertIn("MANAGE-APPROVAL",{c["id"] for c in evaluate(data) if c["status"]=="fail"})
    def test_non_object_manifest_fails_gracefully(self):
        self.assertEqual(evaluate([])[0]["status"],"fail")
if __name__=="__main__":
    unittest.main()
