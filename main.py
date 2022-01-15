from datetime import datetime
from flask import Flask, render_template, redirect, url_for,request,flash,get_flashed_messages,abort
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.simple import EmailField, PasswordField
from wtforms.validators import DataRequired, URL,Email
from flask_ckeditor import CKEditor, CKEditorField
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin,LoginManager,login_user,logout_user,current_user
from functools import wraps
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from flask_gravatar import Gravatar


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

login_manager=LoginManager()
login_manager.init_app(app)

#Login manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#to secure admin only routes
def admin_only(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        #if id is not 1, return abort with 403 error
        if current_user.is_authenticated and int(current_user.id)== 1:
            return f(*args,**kwargs)#continue with the route function
        else:
            return abort(403)
        
    return decorated_function

gravatar = Gravatar(app,size=100,rating='g',default='retro',force_default=False,force_lower=False,use_ssl=False,base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
month=datetime.datetime.now().strftime('%B')
date=datetime.datetime.now().day
year=datetime.datetime.now().year

#User table
class User(db.Model,UserMixin):
    __tablename__='users'
    id = db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(100), nullable=False)
    email=db.Column(db.String(100),nullable=False,unique=True)
    password=db.Column(db.String(100),nullable=False)
    posts=db.relationship('BlogPost',back_populates='author')
    comments=db.relationship('Comment',back_populates='comment_author')

#Blogpost table
class BlogPost(db.Model,UserMixin):
    __tablename__='blog_posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.relationship('User',back_populates='posts')
    author_id=db.Column(db.Integer,ForeignKey('users.id'))
    img_url = db.Column(db.String(250), nullable=False)
    comments=db.relationship('Comment',back_populates='parent_post')

#Comments table
class Comment(db.Model,UserMixin):
    __tablename__='comments'
    id = db.Column(db.Integer, primary_key=True)
    author_id=db.Column(db.Integer,ForeignKey('users.id'))
    text=db.Column(db.Text,nullable=False)
    post_id=db.Column(db.Integer,ForeignKey('blog_posts.id'))
    parent_post=db.relationship('BlogPost',back_populates='comments')
    comment_author=db.relationship('User',back_populates='comments')
    

#db.create_all()

##WTForm
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    author = StringField("Your Name", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")

#WTFORM
class RegisterNewUserForm(FlaskForm):
    name=StringField('Name',validators=[DataRequired()])
    email=EmailField('E-mail Address',validators=[Email()])
    password=PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField("Register")

#WTFORM
class LoginForm(FlaskForm):
    email=EmailField('E-mail Address',validators=[Email()])
    password=PasswordField('Password',validators=[DataRequired()])
    submit = SubmitField("Login")

#WTFORM
class CommentForm(FlaskForm):
    comment=StringField('Add comment')
    submit = SubmitField("Submit")



@app.route('/')
def get_all_posts():
    all_data=db.session.query(BlogPost).all()
    posts=[]
    for post in all_data:
        posts.append(post)
    return render_template("index.html", all_posts=posts,user=current_user)


@app.route('/register',methods=['GET','POST'])
def register():
    form=RegisterNewUserForm()
    if request.method=='POST':
        hashed_password=generate_password_hash(form.password.data,method='pbkdf2:sha256',salt_length=8)

        #if the user tries to register with an existing email
        if User.query.filter_by(email=request.form.get('email')).first():
            flash('The email you entered already exists.Login instead!')
            return redirect(url_for('login'))
        
        else:
            new_user=User(
            name=form.name.data, 
            email=form.email.data,
            password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return render_template('index.html',logged_in=current_user.is_authenticated)
    return render_template('register.html',form=form)


@app.route('/login',methods=['POST','GET'])
def login():
    form=LoginForm()
    if request.method =='POST':
        email=request.form.get('email')
        password=request.form.get('password')
        user_to_login=User.query.filter_by(email=email).first()
        print(user_to_login)

        #if the user's email is in the db
        if user_to_login:
            if check_password_hash(user_to_login.password,password) == True:
                #if the user's password matches that in the db
                login_user(user_to_login) 
                flash('You have succesfully been logged in!')
                return render_template('index.html',logged_in=current_user.is_authenticated)
            else:
                flash('Incorrect credentials! Try again.')
                return redirect(url_for('login'))


        #if the user's email does not exist in the db
        elif not user_to_login:
            flash('Sorry,the Email you entered does not exist.Try again.')
            return redirect(url_for('login'))

        else:
            flash('Incorrect credentials!Try again.')
            return redirect(url_for('login'))

    return render_template('login.html',form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['POST','GET'])
def show_post(post_id):
    form=CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if request.method=='POST':
        comment=form.comment.data
        new_comment=Comment(
            comment_author=current_user,
            parent_post=requested_post,
            text=comment,)
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post,current_user=current_user,form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route('/edit-post/<int:post_id>',methods=['GET','POST'])
@admin_only
def edit_post(post_id):
    post=BlogPost.query.get(post_id)
    edit_form=CreatePostForm(title = post.title,subtitle = post.subtitle,author = post.author,img_url = post.img_url,body = post.body)
    if edit_form.validate_on_submit():
        post.title=edit_form.title.data
        post.subtitle=edit_form.subtitle.data
        post.author=current_user
        post.img_url=edit_form.img_url.data
        post.body=edit_form.body.data
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template('make-post.html',form=edit_form,is_edit=True,current_user=current_user)



@app.route('/new-post',methods=['GET','POST'])
@admin_only
def create_new_post():
    form=CreatePostForm()
    #to fetch data from the form 
    if form.validate_on_submit():
        new_blog_post=BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            author=current_user,
            date=f'{month} {date}, {year}',
            body=form.body.data,
            img_url=form.img_url.data,
        )
        db.session.add(new_blog_post)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template('make-post.html',form=form,current_user=current_user)


@app.route('/delete-post/<int:post_id>',methods=['GET','POST'])
@admin_only
def delete_post(post_id):
    post_to_delete=BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))





if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)