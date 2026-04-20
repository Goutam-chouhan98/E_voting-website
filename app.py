import os
import sqlite3
from datetime import datetime
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "ECI_MP_SecureKey_2024_xK9pL"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Vercel's file system is read-only except for the /tmp directory.
if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/voting.db"
else:
    DB_PATH = os.path.join(BASE_DIR, "voting.db")

EXCEL_PATH = os.path.join(BASE_DIR, "voter_data.xlsx")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin@ECI2024"
MAX_ATTEMPTS = 3


def get_db():
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        campaign_id TEXT PRIMARY KEY,
        campaign_name TEXT NOT NULL,
        constituency TEXT NOT NULL,
        start_dt TEXT NOT NULL,
        end_dt TEXT NOT NULL,
        result_published INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS candidates (
        candidate_id TEXT,
        campaign_id TEXT,
        candidate_name TEXT NOT NULL,
        party_symbol TEXT,
        party_name TEXT NOT NULL,
        additional_info TEXT,
        PRIMARY KEY (candidate_id, campaign_id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS votes (
        campaign_id TEXT,
        voter_id TEXT,
        candidate_id TEXT,
        timestamp TEXT,
        PRIMARY KEY (campaign_id, voter_id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS login_attempts (
        user_id TEXT PRIMARY KEY,
        attempts INTEGER DEFAULT 0,
        locked INTEGER DEFAULT 0
    )""")
    con.commit()
    con.close()

    if not os.path.exists(EXCEL_PATH):
        df = pd.DataFrame({
            'VoterID': ['MP001', 'MP002', 'MP003', 'MP004', 'MP005'],
            'Name': ['Ravi Sharma', 'Sunita Patel', 'Arjun Singh', 'Priya Verma', 'Amit Joshi'],
            'Password': ['pass123', 'mypass', 'vote2024', 'secure1', 'joshi@99']
        })
        df.to_excel(EXCEL_PATH, index=False)
        print("[INFO] voter_data.xlsx created with sample voters.")


def get_lockout(user_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT attempts, locked FROM login_attempts WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    if row:
        return row['attempts'], bool(row['locked'])
    return 0, False


def increment_attempts(user_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT attempts FROM login_attempts WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if row:
        new_att = row['attempts'] + 1
        locked = 1 if new_att >= MAX_ATTEMPTS else 0
        cur.execute("UPDATE login_attempts SET attempts=?, locked=? WHERE user_id=?",
                    (new_att, locked, user_id))
    else:
        new_att = 1
        cur.execute("INSERT INTO login_attempts VALUES (?, 1, 0)", (user_id,))
    con.commit()
    con.close()
    return new_att


def reset_attempts(user_id):
    con = get_db()
    cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO login_attempts VALUES (?, 0, 0)", (user_id,))
    con.commit()
    con.close()


def get_campaign_status(campaign, now):
    if campaign['end_dt'] < now:
        return 'ended'
    elif campaign['start_dt'] > now:
        return 'upcoming'
    return 'active'


# ─── HOME ───────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')


# ─── ADMIN PORTAL ────────────────────────────────────────────────────────

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        attempts, locked = get_lockout('admin')
        if locked:
            flash('Admin account is locked. Contact system administrator.', 'error')
            return render_template('admin/login.html', locked=True)
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            reset_attempts('admin')
            session['admin'] = True
            flash('Welcome, Administrator!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            new_att = increment_attempts('admin')
            remaining = MAX_ATTEMPTS - new_att
            if remaining <= 0:
                flash('Account locked after 3 failed attempts.', 'error')
                return render_template('admin/login.html', locked=True)
            flash(f'Invalid credentials. {remaining} attempt(s) remaining before lockout.', 'error')
    return render_template('admin/login.html', locked=False)


@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM campaigns ORDER BY start_dt DESC")
    campaigns = [dict(c) for c in cur.fetchall()]
    now = datetime.now().isoformat()
    for c in campaigns:
        c['status'] = get_campaign_status(c, now)
        cur.execute("SELECT COUNT(*) as cnt FROM candidates WHERE campaign_id=?", (c['campaign_id'],))
        c['candidate_count'] = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) as cnt FROM votes WHERE campaign_id=?", (c['campaign_id'],))
        c['vote_count'] = cur.fetchone()['cnt']
    con.close()
    return render_template('admin/dashboard.html', campaigns=campaigns)


@app.route('/admin/create_campaign', methods=['GET', 'POST'])
def create_campaign():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        cid = request.form.get('campaign_id', '').strip()
        cname = request.form.get('campaign_name', '').strip()
        constituency = request.form.get('constituency', '').strip()
        start_dt = request.form.get('start_dt', '').strip()
        end_dt = request.form.get('end_dt', '').strip()
        if not all([cid, cname, constituency, start_dt, end_dt]):
            flash('All fields are required.', 'error')
        elif start_dt >= end_dt:
            flash('End date/time must be after start date/time.', 'error')
        else:
            con = get_db()
            cur = con.cursor()
            try:
                cur.execute("INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, 0)",
                            (cid, cname, constituency, start_dt, end_dt))
                con.commit()
                flash(f'Campaign "{cname}" created successfully!', 'success')
                con.close()
                return redirect(url_for('manage_campaign', campaign_id=cid))
            except sqlite3.IntegrityError:
                flash(f'Campaign ID "{cid}" already exists.', 'error')
            finally:
                con.close()
    return render_template('admin/create_campaign.html')


@app.route('/admin/manage_campaign/<campaign_id>', methods=['GET', 'POST'])
def manage_campaign(campaign_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM campaigns WHERE campaign_id=?", (campaign_id,))
    campaign = cur.fetchone()
    if not campaign:
        flash('Campaign not found.', 'error')
        con.close()
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        cand_id = request.form.get('candidate_id', '').strip()
        cand_name = request.form.get('candidate_name', '').strip()
        party_symbol = request.form.get('party_symbol', '').strip()
        party_name = request.form.get('party_name', '').strip()
        additional_info = request.form.get('additional_info', '').strip()
        if not all([cand_id, cand_name, party_name]):
            flash('Candidate ID, Name, and Party Name are required.', 'error')
        else:
            try:
                cur.execute("INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?)",
                            (cand_id, campaign_id, cand_name, party_symbol, party_name, additional_info))
                con.commit()
                flash(f'Candidate "{cand_name}" added!', 'success')
            except sqlite3.IntegrityError:
                flash(f'Candidate ID "{cand_id}" already exists in this campaign.', 'error')
    cur.execute("SELECT * FROM candidates WHERE campaign_id=? ORDER BY candidate_id", (campaign_id,))
    candidates = cur.fetchall()
    con.close()
    return render_template('admin/manage_campaign.html', campaign=campaign, candidates=candidates)


@app.route('/admin/delete_candidate/<campaign_id>/<candidate_id>', methods=['POST'])
def delete_candidate(campaign_id, candidate_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM candidates WHERE campaign_id=? AND candidate_id=?", (campaign_id, candidate_id))
    con.commit()
    con.close()
    flash('Candidate removed.', 'success')
    return redirect(url_for('manage_campaign', campaign_id=campaign_id))


@app.route('/admin/results/<campaign_id>', methods=['GET', 'POST'])
def admin_results(campaign_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    con = get_db()
    cur = con.cursor()
    if request.method == 'POST' and request.form.get('action') == 'publish':
        cur.execute("UPDATE campaigns SET result_published=1 WHERE campaign_id=?", (campaign_id,))
        con.commit()
        flash('Results published successfully!', 'success')
    cur.execute("SELECT * FROM campaigns WHERE campaign_id=?", (campaign_id,))
    campaign = cur.fetchone()
    if not campaign:
        flash('Campaign not found.', 'error')
        con.close()
        return redirect(url_for('admin_dashboard'))
    cur.execute("""
        SELECT c.candidate_id, c.candidate_name, c.party_name, c.party_symbol,
               COUNT(v.voter_id) as vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.candidate_id=v.candidate_id AND c.campaign_id=v.campaign_id
        WHERE c.campaign_id=?
        GROUP BY c.candidate_id ORDER BY vote_count DESC
    """, (campaign_id,))
    results = cur.fetchall()
    total_votes = sum(r['vote_count'] for r in results)
    con.close()
    return render_template('admin/results.html', campaign=campaign, results=results, total_votes=total_votes)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))


# ─── VOTER PORTAL ────────────────────────────────────────────────────────

@app.route('/voter/login', methods=['GET', 'POST'])
def voter_login():
    if session.get('voter_id'):
        return redirect(url_for('voter_dashboard'))
    if request.method == 'POST':
        voter_id = request.form.get('voter_id', '').strip().upper()
        password = request.form.get('password', '').strip()
        attempts, locked = get_lockout(voter_id)
        if locked:
            flash('Your account is locked. Please contact the election administrator.', 'error')
            return render_template('voter/login.html', locked=True)
        try:
            df = pd.read_excel(EXCEL_PATH, dtype=str)
            df['VoterID'] = df['VoterID'].str.strip().str.upper()
            df['Password'] = df['Password'].str.strip()
            voter_row = df[df['VoterID'] == voter_id]
            if not voter_row.empty and voter_row.iloc[0]['Password'] == password:
                reset_attempts(voter_id)
                session['voter_id'] = voter_id
                session['voter_name'] = voter_row.iloc[0]['Name'].strip()
                flash(f"Welcome, {session['voter_name']}!", 'success')
                return redirect(url_for('voter_dashboard'))
            else:
                new_att = increment_attempts(voter_id)
                remaining = MAX_ATTEMPTS - new_att
                if remaining <= 0:
                    flash('Account locked after 3 failed attempts.', 'error')
                    return render_template('voter/login.html', locked=True)
                flash(f'Invalid Voter ID or Password. {remaining} attempt(s) remaining.', 'error')
        except FileNotFoundError:
            flash('Voter database not found. Contact administrator.', 'error')
    return render_template('voter/login.html', locked=False)


@app.route('/voter/dashboard')
def voter_dashboard():
    if not session.get('voter_id'):
        return redirect(url_for('voter_login'))
    voter_id = session['voter_id']
    now = datetime.now().isoformat()
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM campaigns WHERE start_dt<=? AND end_dt>=? ORDER BY end_dt", (now, now))
    campaigns = [dict(c) for c in cur.fetchall()]
    cur.execute("SELECT campaign_id FROM votes WHERE voter_id=?", (voter_id,))
    voted_set = {r['campaign_id'] for r in cur.fetchall()}
    for c in campaigns:
        c['already_voted'] = c['campaign_id'] in voted_set
        cur.execute("SELECT COUNT(*) as cnt FROM candidates WHERE campaign_id=?", (c['campaign_id'],))
        c['candidate_count'] = cur.fetchone()['cnt']
    con.close()
    return render_template('voter/dashboard.html', campaigns=campaigns,
                           voter_name=session.get('voter_name', ''))


@app.route('/voter/vote/<campaign_id>')
def voter_vote(campaign_id):
    if not session.get('voter_id'):
        return redirect(url_for('voter_login'))
    voter_id = session['voter_id']
    now = datetime.now().isoformat()
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM campaigns WHERE campaign_id=? AND start_dt<=? AND end_dt>=?",
                (campaign_id, now, now))
    campaign = cur.fetchone()
    if not campaign:
        flash('This campaign is not currently active.', 'error')
        con.close()
        return redirect(url_for('voter_dashboard'))
    cur.execute("SELECT * FROM votes WHERE campaign_id=? AND voter_id=?", (campaign_id, voter_id))
    if cur.fetchone():
        flash('You have already voted in this campaign.', 'error')
        con.close()
        return redirect(url_for('voter_dashboard'))
    cur.execute("SELECT * FROM candidates WHERE campaign_id=? ORDER BY candidate_id", (campaign_id,))
    candidates = cur.fetchall()
    con.close()
    if not candidates:
        flash('No candidates registered for this campaign yet.', 'error')
        return redirect(url_for('voter_dashboard'))
    return render_template('voter/vote.html', campaign=campaign, candidates=candidates)


@app.route('/voter/confirm_vote', methods=['POST'])
def voter_confirm():
    if not session.get('voter_id'):
        return redirect(url_for('voter_login'))
    campaign_id = request.form.get('campaign_id', '').strip()
    candidate_id = request.form.get('candidate_id', '').strip()
    if not campaign_id or not candidate_id:
        flash('Please select a candidate.', 'error')
        return redirect(url_for('voter_dashboard'))
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM candidates WHERE campaign_id=? AND candidate_id=?",
                (campaign_id, candidate_id))
    candidate = cur.fetchone()
    cur.execute("SELECT * FROM campaigns WHERE campaign_id=?", (campaign_id,))
    campaign = cur.fetchone()
    con.close()
    if not candidate or not campaign:
        flash('Invalid selection. Please try again.', 'error')
        return redirect(url_for('voter_dashboard'))
    return render_template('voter/confirmation.html', candidate=candidate, campaign=campaign)


@app.route('/voter/submit_vote', methods=['POST'])
def voter_submit():
    if not session.get('voter_id'):
        return redirect(url_for('voter_login'))
    voter_id = session['voter_id']
    campaign_id = request.form.get('campaign_id', '').strip()
    candidate_id = request.form.get('candidate_id', '').strip()
    now = datetime.now().isoformat()
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM votes WHERE campaign_id=? AND voter_id=?", (campaign_id, voter_id))
    if cur.fetchone():
        flash('You have already voted in this campaign.', 'error')
        con.close()
        return redirect(url_for('voter_dashboard'))
    cur.execute("SELECT * FROM campaigns WHERE campaign_id=? AND start_dt<=? AND end_dt>=?",
                (campaign_id, now, now))
    if not cur.fetchone():
        flash('This campaign is no longer active.', 'error')
        con.close()
        return redirect(url_for('voter_dashboard'))
    try:
        cur.execute("INSERT INTO votes VALUES (?, ?, ?, ?)", (campaign_id, voter_id, candidate_id, now))
        con.commit()
    except sqlite3.IntegrityError:
        flash('Vote already recorded.', 'error')
        con.close()
        return redirect(url_for('voter_dashboard'))
    con.close()
    return redirect(url_for('voter_thankyou'))


@app.route('/voter/thankyou')
def voter_thankyou():
    if not session.get('voter_id'):
        return redirect(url_for('voter_login'))
    return render_template('voter/thankyou.html', voter_name=session.get('voter_name', ''))


@app.route('/voter/logout')
def voter_logout():
    session.pop('voter_id', None)
    session.pop('voter_name', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
