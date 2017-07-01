# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
		render_template, flash
from oauth2client import client, GOOGLE_TOKEN_URI, GOOGLE_REVOKE_URI
from apiclient.discovery import build
import httplib2
import datetime
import json


app = Flask(__name__) # create the application instance
app.config.from_object(__name__) # load config from this file , flask_page.py


with open('client_secrets.json') as secret_file:
	secrets = json.load(secret_file)

# Load default config and override config from an environment variable
app.config.update(dict(
	DATABASE=os.path.join(app.root_path, 'flask_page.db'),
	SECRET_KEY='development key',
	USERNAME='admin',
	PASSWORD='default',
	CLIENT_ID=secrets['web']['client_id'],			# Load client id from file
	CLIENT_SECRET=secrets['web']['client_secret']	# Load client secret from file
)),
app.config.from_envvar('FLASK_PAGE_SETTINGS', silent=True)


@app.route('/')
def show_main_page():
	db = get_db()
	cur = db.execute('select title, link, text, id from sites order by id desc')
	sites = cur.fetchall()
	cur = db.execute('select title, text, id from notes order by id desc')
	notes = cur.fetchall()
	events = get_calendar()

	return render_template('show_main_page.html', sites=sites, notes=notes, events=events)

def connect_db():
	"""Connects to the specific database."""
	rv = sqlite3.connect(app.config["DATABASE"])
	rv.row_factory = sqlite3.Row
	return rv

def init_db():
	db = get_db()
	with app.open_resource('schema.sql', mode='r') as f:
		db.cursor().executescript(f.read())
	db.commit()

@app.cli.command('initdb')
def initdb_command():
	"""Initializes the database."""
	init_db()
	print('Initialized the database.')

def get_db():
	"""Opens a new database connection if there is none yet for the
	current application context.
	"""
	if not hasattr(g, 'sqlite_db'):
		g.sqlite_db = connect_db()
	return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
	"""Closes the database again at the end of the request."""
	if hasattr(g, 'sqlite_db'):
		g.sqlite_db.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
	error = None
	if request.method == 'POST':
		if request.form['username'] != app.config['USERNAME']:
			error = 'Invalid username'
		elif request.form['password'] != app.config['PASSWORD']:
			error = 'Invalid password'
		else:
			session['logged_in'] = True
			return redirect(url_for('show_main_page'))
	return render_template('login.html', error=error)

@app.route('/logout')
def logout():
	session.pop('logged_in', None)
	return redirect(url_for('show_main_page'))

@app.route('/add_website', methods=['GET', 'POST'])
def add_website():
	error=None
	if request.method == 'POST':
		if not session.get('logged_in'):
			abort(401)
		db = get_db()
		db.execute('insert into sites (title, link, text) values (?, ?, ?)',
					 [request.form['title'], request.form['link'], request.form['text']])
		db.commit()
		return redirect(url_for('show_main_page'))
	return render_template('add_website.html')

@app.route('/delete_site/<int:site_id>', methods=['POST'])
def delete_site(site_id):
	if not session.get('logged_in'):
		abort(401)
	db = get_db()
	db.execute('delete from sites where id=' + str(site_id))
	db.commit()
	return redirect(url_for('show_main_page'))

@app.route('/edit_site/<int:edit_site_id>', methods=['GET', 'POST'])
def edit_site(edit_site_id):
	error=None
	if request.method == 'POST':
		if not session.get('logged_in'):
			abort(401)
		db = get_db()
		db.execute('update sites set title=?,link=?,text=? where id=?',
			[request.form['title'], request.form['link'], request.form['text'], str(edit_site_id)])
		db.commit()
		return redirect(url_for('show_main_page'))
	else:
		if not session.get('logged_in'):
			abort(401)
		db = get_db()
		cur = db.execute('select title, link, text from sites where id=' + str(edit_site_id))
		site = cur.fetchone()
		return render_template('edit_site.html', site=site, site_id=edit_site_id)

@app.route('/add_note', methods=['GET', 'POST'])
def add_note():
	error=None
	if request.method == 'POST':
		if not session.get('logged_in'):
			abort(401)
		db = get_db()
		db.execute('insert into notes (title, text) values (?, ?)',
					 [request.form['title'], request.form['text']])
		db.commit()
		return redirect(url_for('show_main_page'))
	return render_template('add_note.html')

@app.route('/delete_note/<int:del_note_id>', methods=['POST'])
def delete_note(del_note_id):
	if not session.get('logged_in'):
		abort(401)
	db = get_db()
	db.execute('delete from notes where id=' + str(del_note_id))
	db.commit()
	return redirect(url_for('show_main_page'))

@app.route('/edit_note/<int:edit_note_id>', methods=['GET', 'POST'])
def edit_note(edit_note_id):
	error=None
	if request.method == 'POST':
		if not session.get('logged_in'):
			abort(401)
		db = get_db()
		db.execute('update notes set title=?,text=? where id=?',
			[request.form['title'], request.form['text'], str(edit_note_id)])
		db.commit()
		return redirect(url_for('show_main_page'))
	else:
		if not session.get('logged_in'):
			abort(401)
		db = get_db()
		cur = db.execute('select title, text from notes where id=' + str(edit_note_id))
		note = cur.fetchone()
		return render_template('edit_note.html', note=note, note_id=edit_note_id)

# See https://developers.google.com/google-apps/calendar/quickstart/python
# https://developers.google.com/api-client-library/python/auth/web-app
# https://stackoverflow.com/questions/22915461/google-login-server-side-flow-storing-credentials-python-examples
@app.route('/oauth2callback')
def oauth2callback():
	flow = client.flow_from_clientsecrets(
		'client_secrets.json',
		scope='https://www.googleapis.com/auth/calendar.readonly',
		redirect_uri='http://127.0.0.1:5000/oauth2callback',
		prompt='consent')
	flow.params['access_type'] = 'offline'			# offline access
	flow.params['include_granted_scopes'] = 'true'	# incremental auth

	if  (request.args.get('error')):
		flash('Google login failed')
	elif 'code' not in request.args:
		auth_uri = flow.step1_get_authorize_url()
		return redirect(auth_uri)
	else:
		auth_code = request.args.get('code')
		credentials = flow.step2_exchange(auth_code)
		session['access_token'] = credentials.access_token
		session['refresh_token'] = credentials.refresh_token

		expires_in = credentials.get_access_token().expires_in
		print('access_token:', credentials.get_access_token())
		session['expire_time'] = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)

		flash('Google login succeeded')
	return redirect(url_for('show_main_page'))

def get_calendar():
	if not 'access_token' in session:
		print('no access token')
		return []

	if session['expire_time'] < datetime.datetime.now():
		(session['access_token'], expires_in) = refresh_access_token()
		session['expire_time'] = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)

	credentials = client.AccessTokenCredentials(session['access_token'], 'user-agent-value')

	http_auth = credentials.authorize(httplib2.Http())
	service = build('calendar', 'v3', http=http_auth)
	now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
	time_max = (datetime.datetime.now() + datetime.timedelta(days=7)).isoformat() + 'Z'
	
	eventsResult = service.events().list(
		calendarId='primary', timeMin=now, timeMax=time_max, singleEvents=True,
		orderBy='startTime').execute()
	events = eventsResult.get('items', [])

	appointments = []
	for event in events:
		if (event['start'].get('dateTime')):
			appointment = {}
			
			rcf_start = event['start'].get('dateTime')
			start = datetime.datetime.strptime(rcf_start, '%Y-%m-%dT%H:%M:%S-07:00')
			appointment['start_day'] = start.strftime("%a")
			appointment['start_date'] = start.strftime("%Y-%m-%d")
			appointment['start_time'] = start.strftime("%-I:%M")

			rcf_end = event['end'].get('dateTime')
			end = datetime.datetime.strptime(rcf_end, '%Y-%m-%dT%H:%M:%S-07:00')
			appointment['end_time'] = end.strftime("%-I:%M")
			appointment['summary'] = event['summary']

			appointments.append(appointment)
	return appointments;

# https://stackoverflow.com/questions/27771324/google-api-getting-credentials-from-refresh-token-with-oauth2client-client
def refresh_access_token():
	print('hi')

	credentials = client.OAuth2Credentials(
	    None, app.config['CLIENT_ID'], app.config['CLIENT_SECRET'], session['refresh_token'], None, GOOGLE_TOKEN_URI,
	    None, revoke_uri=GOOGLE_REVOKE_URI)

	# refresh the access token (or just try using the service)
	credentials.refresh(httplib2.Http())
	print(credentials.to_json())

	return (credentials.access_token, credentials.get_access_token().expires_in)