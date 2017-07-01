# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
		render_template, flash

app = Flask(__name__) # create the application instance
app.config.from_object(__name__) # load config from this file , flask_page.py

# Load default config and override config from an environment variable
app.config.update(dict(
	DATABASE=os.path.join(app.root_path, 'flask_page.db'),
	SECRET_KEY='development key',
	USERNAME='admin',
	PASSWORD='default'
))
app.config.from_envvar('FLASK_PAGE_SETTIGNS', silent=True)

@app.route('/')
def show_main_page():
	db = get_db()
	cur = db.execute('select title, link, text, id from sites order by id desc')
	sites = cur.fetchall()
	cur = db.execute('select title, text, id from notes order by id desc')
	notes = cur.fetchall()
	return render_template('show_main_page.html', sites=sites, notes=notes)

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
	print(request.method, edit_site_id)
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
	print(request.method, edit_note_id)
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