from flask import Flask, jsonify, render_template, request, flash, redirect, url_for, abort
from flask_gravatar import Gravatar
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy.orm import relationship
from functools import wraps
from forms import CreateCafeForm, RegisterForm, LoginForm, CommentForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'Your key'

##Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
ckeditor = CKEditor(app)
Bootstrap(app)


##Cafe TABLE Configuration
class Cafe(db.Model):
    __tablename__ = "cafes"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="cafes")
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, default=False, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=True)
    # ***************Parent Relationship*************#
    comments = relationship("Comment", back_populates="parent_cafe")

    def to_dict(self):
        dictionary = {column.name: getattr(self, column.name) for column in self.__table__.columns}
        return dictionary

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    cafes = relationship("Cafe", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

with app.app_context():
    db.create_all()


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    date = db.Column(db.Text)

    # ***************Child Relationship*************#
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafes.id"))
    parent_cafe = relationship("Cafe", back_populates="comments")
    text = db.Column(db.Text, nullable=True)
with app.app_context():
    db.create_all()

login_manager = LoginManager(app)
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            # User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        password = form.password.data
        hash_password = generate_password_hash(password=password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hash_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form_log = LoginForm()
    if form_log.validate_on_submit():
        try:
            email = form_log.email.data
            user = User.query.filter_by(email=email).first()
            password = form_log.password.data
            if user and check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home'))
            else:
                flash('Invalid Password, please try again.')
        except AttributeError:
            flash('The email does not exist, please try again.')
    return render_template("login.html", form=form_log, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/")
def home():
    all_cafe = Cafe.query.all()
    all_locations = list(set([cafe.location for cafe in all_cafe])) #delete duplicates
    return render_template("index.html", loc=all_locations)


@app.route("/all_cafes")
def see_all_cafes():
    cafes = db.session.query(Cafe).all()
    cafes = [cafe.to_dict() for cafe in cafes]
    return render_template("all_cafes.html", cafes=cafes)


@app.route("/location/<loct>", methods=["GET", "POST"])
def show_cafe_at_location(loct):
    query_location = db.session.query(Cafe).filter(Cafe.location == loct)
    cafes = [cafe.to_dict() for cafe in query_location]
    return render_template("all_cafes.html", cafes=cafes)


@app.route("/new-cafe", methods=["GET", "POST"])
@admin_only
def add_new_cafe():
    form = CreateCafeForm()
    if form.validate_on_submit():
        new_cafe = Cafe(
            name=form.name.data,
            map_url=form.map_url.data,
            img_url=form.img_url.data,
            location=form.location.data,
            author=current_user,
            seats=form.seats.data,
            has_toilet=form.has_toilet.data,
            has_wifi=form.has_wifi.data,
            has_sockets=form.has_sockets.data,
            can_take_calls=form.can_take_calls.data,
            coffee_price=form.coffee_price.data,

        )
        db.session.add(new_cafe)
        db.session.commit()
        return redirect(url_for("see_all_cafes"))
    return render_template("add_cafe.html", form=form, current_user=current_user)


## HTTP DELETE - Delete Record
@app.route("/delete/<int:cafe_id>")
@admin_only
def delete_cafe(cafe_id):
    cafe_to_delete = Cafe.query.get(cafe_id)
    db.session.delete(cafe_to_delete)
    db.session.commit()
    return redirect(url_for("see_all_cafes"))


## HTTP EDIT - Edit Record
@app.route("/edit_cafe/<int:cafe_id>", methods=["GET", "POST"])
@admin_only
def edit_cafe(cafe_id):
    cafe = Cafe.query.get(cafe_id)
    edit_form = CreateCafeForm(
        name=cafe.name,
        map_url=cafe.map_url,
        img_url=cafe.img_url,
        location=cafe.location,
        seats=cafe.seats,
        has_toilet=cafe.has_toilet,
        has_wifi=cafe.has_wifi,
        has_sockets=cafe.has_sockets,
        can_take_calls=cafe.can_take_calls,
        coffee_price=cafe.coffee_price,
    )
    if edit_form.validate_on_submit():
        cafe.id = cafe_id
        cafe.name = edit_form.name.data
        cafe.author = current_user
        cafe.map_url = edit_form.map_url.data
        cafe.img_url = edit_form.img_url.data
        cafe.location = edit_form.location.data
        cafe.seats = edit_form.seats.data
        cafe.has_toilet = edit_form.has_toilet.data
        cafe.has_wifi = edit_form.has_wifi.data
        cafe.has_sockets = edit_form.has_sockets.data
        cafe.can_take_calls = edit_form.can_take_calls.data
        cafe.coffee_price = edit_form.coffee_price.data
        db.session.commit()
        return redirect(url_for("show_cafe", cafe_id=cafe.id))

    return render_template("add_cafe.html", form=edit_form, is_edit=True, current_user=current_user)

## HTTP GET - Read Record

@app.route("/cafe/<int:cafe_id>", methods=["GET", "POST"])
def show_cafe(cafe_id):
    requested_cafe = Cafe.query.get(cafe_id)
    all_comments = Comment.query.all()
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(text=form.comment.data, author_id=current_user.id, cafe_id=requested_cafe.id, date=datetime.today().strftime('%Y-%m-%d'))
            db.session.add(new_comment)
            db.session.commit()
        else:
            flash('You need to log in or register.')
            return redirect(url_for('login'))
    return render_template("cafe.html", cafe=requested_cafe, current_user=current_user, form=form, comments=all_comments)





if __name__ == '__main__':
    app.run(debug=True)
