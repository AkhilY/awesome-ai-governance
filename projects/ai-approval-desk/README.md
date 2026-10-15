# AI Approval Desk

A working local AI governance register built with Flask and SQLite. Organizations describe an AI use, inspect explainable review flags, and record a human decision with a rationale. No AI API key is needed.

## Run

Requires Python 3.10 or later. From this directory:

```sh
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5001. Select **Load demo proposals** on the empty dashboard to create three fictional senior-center scenarios. Demo loading never overwrites an existing register.

## Included

- Seven required intake questions with Yes / No / Not sure answers.
- Versioned, deterministic concern flags with reasons and suggested actions.
- Dashboard with decision filtering and counts.
- Human approval, changes requested, or decline; named reviewer and rationale required.
- Append-only decision history through the application; exports include original intake, rule assessment, UTC timestamps, and all decisions.
- SQLite persistence, escaped templates, CSRF tokens, host validation, and security headers.

## Try the workflow

1. Load the examples and open Participant records assistant.
2. Inspect privacy, impact, oversight, and accessibility concerns.
3. Record Changes requested with conditions for a privacy review and named owner.
4. Record a later decision and confirm both entries remain in the history.
5. Download the JSON record.

## Rules and boundaries

`assess()` in `app.py` contains rule set 1.0. Sensitive data, consequential decisions, or missing human oversight trigger High concern. Public interaction, vulnerable users, missing accessible alternatives, incomplete vendor review, and unknown answers trigger Moderate concern. Otherwise concern is Low. The highest triggered concern wins; this is a transparent demo heuristic, not a validated risk model or legal classification. Assessments are saved with their rule version when a proposal is created.

The app supports governance of AI; it does not use an AI model to make approvals. A human can record any decision, including approval with unresolved flags; their rationale documents responsibility.

This is a **single-user local prototype**. Bind only to loopback and use fictional data. It has no login, verified reviewer identity, access controls, encryption at rest, or tamper-proof audit storage. Anyone with local access to the app or database can access records. Before shared deployment, add authentication, roles, secure secrets, TLS, backup/retention policies, and independently protected audit storage. No proposal editing/deletion or external calls are provided. Session keys are random per process unless SECRET_KEY is supplied, so restarting invalidates open forms.

## Test

```sh
python -m unittest discover -s tests -v
```

Tests exercise persistence, review history and exports, validation, CSRF rejection, HTML escaping, missing records, demo idempotency, and concern rules.
