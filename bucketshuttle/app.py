""":mod:`bucketshuttle.app` --- Web server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""
import re
import os
import time
import logging
import zipfile
import datetime

from flask import (Flask, abort, current_app, redirect, request,
                   render_template, session, url_for, make_response)
from flask.helpers import send_from_directory
from flask_oauthlib.client import OAuth


REQUIRED_CONFIGS = ('REPOSITORY', 'OAUTH', 'SAVE_DIRECTORY', 'SECRET_KEY')
EXPIRES = datetime.timedelta(minutes=5)

app = Flask(__name__)

oauth = OAuth()

bitbucket = oauth.remote_app(
    'bitbucket',
    base_url='https://bitbucket.org/api/1.0/',
    request_token_url='https://bitbucket.org/!api/1.0/oauth/request_token',
    access_token_url='https://bitbucket.org/!api/1.0/oauth/access_token',
    authorize_url='https://bitbucket.org/!api/1.0/oauth/authenticate',
    app_key='OAUTH',
)

oauth.init_app(app)


@bitbucket.tokengetter
def get_bitbucket_token():
    if 'bitbucket_oauth' in session:
        resp = session['bitbucket_oauth']
        return resp['oauth_token'], resp['oauth_token_secret']


def open_file(filename, mode='r', config=None):
    config = config or current_app.config
    save_path = config['SAVE_DIRECTORY']
    if not os.path.isdir(save_path):
        os.makedirs(save_path)
    return open(os.path.join(save_path, filename), mode)


def open_head_file(mode='r', config=None):
    return open_file('head.txt', mode, config=config)


def get_head(config=None):
    try:
        with open_head_file(config=config) as f:
            return f.read().strip()
    except IOError:
        pass


def ensure_login():
    logger = logging.getLogger(__name__ + '.ensure_login')
    if get_bitbucket_token() is None:
        session.pop('access', None)
        callback_url = url_for('auth', _external=True, next=request.url)
        return bitbucket.authorize(
            callback=callback_url
        )
    try:
        auth, ltime = session['access']
    except (KeyError, ValueError):
        auth = False
        ltime = None
    if ltime is None or ltime < datetime.datetime.utcnow() - EXPIRES:
        repo_name = current_app.config['REPOSITORY']
        # user repos
        response = bitbucket.request('user/repositories')
        if response.status != 200:
            abort(401)
        repo_dicts = response.data
        repos = frozenset(
            repo['owner'] + '/' + repo['slug']
            for repo in repo_dicts
        )
        logger.debug('repos = %r', repos)
        auth = repo_name in repos
        session['access'] = auth, datetime.datetime.utcnow()
    if not auth:
        abort(403)
    logger.debug('auth = %r', auth)


@app.route('/')
def home():
    next = ensure_login()
    if next:
        return next
    head = get_head()
    if head is None:
        return render_template('empty.html')
    save_dir = current_app.config['SAVE_DIRECTORY']
    refs = {}
    time_fmt = '%Y-%m-%dT%H:%M:%SZ'
    build_logs = {}
    for name in os.listdir(save_dir):
        if re.match(r'^[A-Fa-f0-9]{40}$', name):
            fullname = os.path.join(save_dir, name)
            stat = os.stat(fullname)
            refs[name] = time.strftime(time_fmt, time.gmtime(stat.st_mtime))
            build_logs[name] = os.path.isfile(
                os.path.join(fullname, 'build.txt')
            )
    return render_template('list.html',
                           head=head, refs=refs, build_logs=build_logs)


@app.route('/<ref>/', defaults={'path': 'index.html'})
@app.route('/<ref>/<path:path>')
def docs(ref, path):
    if ref == 'head':
        ref = get_head()
        if ref is None:
            abort(404)
    elif not re.match(r'^[A-Fa-f0-9]{7,40}$', ref):
        abort(404)
    next = ensure_login()
    if next:
        return next
    save_dir = current_app.config['SAVE_DIRECTORY']
    if len(ref) < 40:
        for candi in os.listdir(save_dir):
            if (os.path.isdir(os.path.join(save_dir, candi)) and
                    candi.startswith(ref)):
                return redirect(url_for('docs', ref=candi, path=path))
        abort(404)
    return send_from_directory(save_dir, os.path.join(ref, path))


@app.route('/auth/finalize')
@bitbucket.authorized_handler
def auth(resp):
    if resp is None:
        abort(401)
    session['bitbucket_oauth'] = resp
    next = request.args.get('next', url_for('home'))
    return redirect(next)


@app.route('/', methods=['POST'])
def upload():
    commit = request.form['commit']
    data = request.files['file']

    # Unzip
    zfile = zipfile.ZipFile(file=data)
    save_dir = current_app.config['SAVE_DIRECTORY']
    dirpath = os.path.join(save_dir, commit)
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)
    for name in zfile.namelist():
        dirname, filename = os.path.split(name)
        directory = os.path.join(dirpath, dirname)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(os.path.join(directory, filename), 'w') as f:
            f.write(zfile.read(name))
    # Update head
    with open(os.path.join(save_dir, 'head.txt'), 'w') as f:
        f.write(commit)

    response = make_response('true', 202)
    response.mimetype = 'application/json'
    return response
