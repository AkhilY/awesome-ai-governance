# AI Governance Gatekeeper

Zero-dependency Python documentation gate inspired by the Govern, Map, Measure and Manage functions of NIST AI RMF.

Run in this folder:
```bash
python3 -m unittest discover -s tests -v
python3 -m governance.check examples/senior_assistant.json
python3 -m governance.check examples/incomplete_assistant.json  # expected failure
```

Eleven checks validate declarations covering owner, purpose, data sources, privacy, evaluation, fairness, incident response, risk level, and additional high-risk oversight, approval, and mitigation. All references are self-declared and are **not authenticated**. Passing is not proof of safety, fairness, approval, or compliance.

GitHub workflow: `.github/workflows/ai-governance-gatekeeper.yml`.
