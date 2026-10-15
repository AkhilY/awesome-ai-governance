"""Local AI governance intake and human decision register."""
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, abort, g, redirect, render_template, request, session, url_for, Response

QUESTIONS = {
    'sensitive': 'Will it process personal, health, financial, or identity data?',
    'consequential': 'Will it influence access to services or other consequential decisions?',
    'public': 'Will people interact directly with its answers?',
    'vulnerable': 'Will it serve older adults or other people needing additional support?',
    'human': 'Will a named person check outputs and handle complaints?',
    'accessible': 'Are accessible alternatives and a way to reach staff available?',
    'vendor': 'Have vendor data use, retention, and deletion terms been reviewed?',
}
RULE_VERSION = '1.0'

def assess(answers):
    flags = []
    rules = [
        ('sensitive', 'yes', 'High', 'Privacy review', 'Minimize data; document purpose, access, retention, and deletion.'),
        ('consequential', 'yes', 'High', 'Impact review', 'Require human review, fairness testing, and a way to challenge decisions.'),
        ('public', 'yes', 'Moderate', 'Public-facing reliability', 'Disclose AI use, test common errors, and provide staff escalation.'),
        ('vulnerable', 'yes', 'Moderate', 'Inclusive design review', 'Test with intended users and document accessibility and support needs.'),
        ('human', 'no', 'High', 'Oversight missing', 'Assign an accountable owner and a complaint response process.'),
        ('accessible', 'no', 'Moderate', 'Alternative access missing', 'Provide an accessible, non-AI route to the same service.'),
        ('vendor', 'no', 'Moderate', 'Vendor review incomplete', 'Review supplier data practices and record the agreement.'),
    ]
    for key, trigger, level, title, action in rules:
        if answers.get(key) == trigger:
            flags.append(dict(level=level, title=title, action=action))
    for key, label in QUESTIONS.items():
        if answers.get(key) == 'unknown':
            flags.append(dict(level='Moderate', title=f'Unanswered: {label}', action='Resolve this uncertainty before approval.'))
    level = 'High' if any(f['level'] == 'High' for f in flags) else 'Moderate' if flags else 'Low'
    return dict(level=level, flags=flags, rule_version=RULE_VERSION)

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32), DATABASE=str(Path(__file__).parent / 'instance' / 'desk.sqlite3'), MAX_CONTENT_LENGTH=64 * 1024, SESSION_COOKIE_SAMESITE='Strict', TRUSTED_HOSTS=['localhost', '127.0.0.1'])
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(error):
        connection = g.pop('db', None)
        if connection:
            connection.close()

    with app.app_context():
        db().executescript('''CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, title TEXT NOT NULL, owner TEXT NOT NULL, purpose TEXT NOT NULL, answers TEXT NOT NULL, assessment TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY, proposal_id INTEGER NOT NULL REFERENCES proposals(id), status TEXT NOT NULL, reviewer TEXT NOT NULL, rationale TEXT NOT NULL, created_at TEXT NOT NULL);''')
        db().commit()

    @app.before_request
    def csrf():
        session.setdefault('csrf', secrets.token_hex(32))
        if request.method == 'POST' and not secrets.compare_digest(session['csrf'], request.form.get('csrf', '')):
            abort(400, 'Invalid form token. Reload the page and try again.')

    @app.after_request
    def headers(response):
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response

    def proposal(pid):
        row = db().execute('SELECT * FROM proposals WHERE id=?', (pid,)).fetchone()
        if row is None:
            abort(404)
        data = dict(row)
        data['answers'] = json.loads(data['answers'])
        data['assessment'] = json.loads(data['assessment'])
        data['decisions'] = [dict(r) for r in db().execute('SELECT * FROM decisions WHERE proposal_id=? ORDER BY id DESC', (pid,))]
        data['status'] = data['decisions'][0]['status'] if data['decisions'] else 'Pending review'
        return data

    def insert(title, owner, purpose, answers):
        cursor = db().execute('INSERT INTO proposals(title,owner,purpose,answers,assessment,created_at) VALUES (?,?,?,?,?,?)', (title, owner, purpose, json.dumps(answers), json.dumps(assess(answers)), now()))
        db().commit()
        return cursor.lastrowid

    @app.get('/')
    def index():
        items = [proposal(r['id']) for r in db().execute('SELECT id FROM proposals ORDER BY id DESC')]
        status = request.args.get('status', '')
        visible = [p for p in items if not status or p['status'] == status]
        return render_template('index.html', items=visible, total=len(items), pending=sum(p['status'] == 'Pending review' for p in items), high=sum(p['assessment']['level'] == 'High' for p in items), status=status)

    @app.route('/new', methods=['GET', 'POST'])
    def new():
        error = None
        if request.method == 'POST':
            fields = {k: request.form.get(k, '').strip() for k in ('title', 'owner', 'purpose')}
            answers = {k: request.form.get(k) for k in QUESTIONS}
            if any(not v or len(v) > 2000 for v in fields.values()) or any(v not in ('yes', 'no', 'unknown') for v in answers.values()):
                error = 'Complete every field (maximum 2,000 characters each) and answer every question.'
            else:
                return redirect(url_for('detail', pid=insert(**fields, answers=answers)))
        return render_template('new.html', questions=QUESTIONS, error=error)

    @app.get('/proposals/<int:pid>')
    def detail(pid):
        return render_template('detail.html', p=proposal(pid), questions=QUESTIONS)

    @app.post('/proposals/<int:pid>/decision')
    def decision(pid):
        proposal(pid)
        status = request.form.get('status')
        reviewer = request.form.get('reviewer', '').strip()
        rationale = request.form.get('rationale', '').strip()
        if status not in ('Approved', 'Changes requested', 'Declined') or not reviewer or not rationale or max(len(reviewer), len(rationale)) > 2000:
            abort(400, 'Choose a decision and supply a reviewer and rationale (maximum 2,000 characters).')
        db().execute('INSERT INTO decisions(proposal_id,status,reviewer,rationale,created_at) VALUES (?,?,?,?,?)', (pid, status, reviewer, rationale, now()))
        db().commit()
        return redirect(url_for('detail', pid=pid))

    @app.get('/proposals/<int:pid>/export')
    def export(pid):
        data = proposal(pid)
        data['record_note'] = 'Heuristic governance triage; not a legal or regulatory compliance determination. Reviewer identity is self-reported in this local demo.'
        return Response(json.dumps(data, indent=2), mimetype='application/json', headers={'Content-Disposition': f'attachment; filename=ai-decision-{pid}.json'})

    @app.post('/demo')
    def demo():
        if db().execute('SELECT COUNT(*) FROM proposals').fetchone()[0] == 0:
            base = dict(sensitive='no', consequential='no', public='no', vulnerable='no', human='yes', accessible='yes', vendor='yes')
            for title, purpose, overrides in [
                ('Class description writer', 'Draft class descriptions from public program information. A staff member edits every draft.', {}),
                ('Senior center information chatbot', 'Answer public opening-hours and class questions, with a route to speak to staff.', dict(public='yes', vulnerable='yes', vendor='unknown')),
                ('Participant records assistant', 'Summarize fictional participant records to help staff prioritize service eligibility.', dict(sensitive='yes', consequential='yes', vulnerable='yes', human='no', accessible='unknown', vendor='no')),
            ]:
                insert(title, 'Demo program coordinator', purpose, base | overrides)
        return redirect(url_for('index'))
    return app

if __name__ == '__main__':
    create_app().run(host='127.0.0.1', port=5001, debug=False)
