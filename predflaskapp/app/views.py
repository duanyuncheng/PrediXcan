from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm, oid
from forms import LoginForm, EditForm, PostForm, CommandGenForm
from models import User, Post
from datetime import datetime
from helpers import *

@app.route('/login',methods=['GET','POST'])
@oid.loginhandler
def login():
	if g.user is not None and g.user.is_authenticated():
		return redirect(url_for('index'))
	form = LoginForm()
	if form.validate_on_submit():
		session['remember_me'] = form.remember_me.data
		return oid.try_login(form.openid.data, ask_for=['nickname', 'email'])
		"""
		flash('Login requested for jankyID="%s", remember_me=%s' %	
			(form.openid.data, str(form.remember_me.data)))
		return redirect('/index') 
		"""
	return render_template('login.html',title='Sign In',form=form,providers=app.config['OPENID_PROVIDERS'])

@app.route('/edit', methods=['GET','POST'])
@login_required
def edit():
	form = EditForm(g.user.nickname)
	if form.validate_on_submit():
		g.user.nickname = form.nickname.data
		g.user.about_me = form.about_me.data
		db.session.add(g.user)
		db.session.commit()
		flash("Ch-ch-ch changes saved.")
		#return redirect(url_for('edit'))
		return redirect('user/' + g.user.nickname)
	else:
		form.nickname.data = g.user.nickname
		form.about_me.data = g.user.about_me
	return render_template('edit.html',form=form)

@app.route('/newpost', methods=['GET','POST'])
@login_required 
def post():
	form = PostForm()
	if form.validate_on_submit(): 
		body = form.post_text.data 
		p = Post(body=body, timestamp = datetime.utcnow(), author = g.user) #correct author ?
		db.session.add(p)
		db.session.commit()
		flash("Successfully posted!")
		return redirect('user/' + g.user.nickname)
	
	return render_template('newpost.html',form=form) # jump to the actual url

@oid.after_login
def after_login(resp):
	if resp.email is None or resp.email == "":
		flash('invalid login. please try again.')
		return redirect(url_for('login'))
	user = User.query.filter_by(email=resp.email).first()
	if user is None:
		nickname = resp.nickname
		if nickname is None or nickname == "":
			nickname = resp.email.split('@')[0]
		nickname = User.make_unique_nickname(nickname)
		user = User(nickname=nickname,email=resp.email)
		db.session.add(user)
		db.session.commit()
	remember_me = False
	if 'remember_me' in session:
		remember_me = session['remember_me']
		session.pop('remember_me',None)
	login_user(user, remember = remember_me)
	return redirect(request.args.get('next') or url_for('index'))

@app.before_request
def before_request():
	g.user = current_user
	if g.user.is_authenticated():
		g.user.last_seen = datetime.utcnow()
		db.session.add(g.user)
		db.session.commit()

@app.route('/')
@app.route('/index')
@login_required
def index():
    user = g.user
    posts = [ 
	    {
	    	'author':{'nickname':'John'},
	    	'body': 'Beautiful day in Portland!'

	    },
	    {
	    	'author': {'nickname':'Susan'},
	    	'body': 'Whats going on?'
	    }
    ]
    return render_template('index.html',
    						title='home',
    						user=user,
    						posts=posts)

@lm.user_loader
def load_user(id):
	return User.query.get(int(id))

@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/gencmd', methods=['GET','POST'])
def gen_command():
	form = CommandGenForm()
	form.tissuetype.choices = _getTissueTypes() #fetch tissue types from DB
	form.study.choices = _getStudyNames() #fetch study names from DB

	if form.validate_on_submit():
		#printCommandline(stuff from forms)
	return render_template('cmdgen.html',form=form) #TBA


"""here lie user profiles"""
@app.route('/user/<nickname>')
@login_required
def user(nickname):
	user = User.query.filter_by(nickname=nickname).first()
	if user == None: 
		flash('user %s not found.' % nickname)
		return redirect(url_for('index'))
	posts = user.posts.all()
	return render_template('user.html', user=user, posts=posts)

"""Here lie error handlers"""
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500