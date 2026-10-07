from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth

import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "your_secret_key" 


UPLOAD_SUBFOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", UPLOAD_SUBFOLDER)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///admin.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



def _build_unique_username(base_name):
    clean = (base_name or "user").strip().lower().replace(" ", "_")
    clean = "".join(ch for ch in clean if ch.isalnum() or ch == "_")
    clean = clean[:20] or "user"

    username = clean
    while Admin.query.filter_by(username=username).first():
        username = f"{clean}_{uuid.uuid4().hex[:6]}"
    return username


def _split_name(full_name):
    parts = (full_name or "").strip().split()
    if not parts:
        return "User", "Account"
    if len(parts) == 1:
        return parts[0], "Account"
    return parts[0], " ".join(parts[1:])



#database model
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    username= db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password,  method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

   




#Routes

@app.route("/")
def home():
    if "username" in session: #alreaddy logged in
      return redirect(url_for('dashboard'))
    return render_template("index.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    admin= Admin.query.filter_by(username=username).first()

    if not admin:
        return render_template("index.html", message="User not found, please register!", show_register=True)
   
    if not admin.check_password(password):
        return render_template("index.html", error="Invalid username or password!")
    
    if admin and admin.check_password(password):
        session['username']=username
        return redirect(url_for('dashboard'))




@app.route("/register", methods=["GET", "POST"])  
   
def register():

    if request.method == "GET":
        return render_template("index.html", show_register=True)
    

    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    
    if not all([first_name, last_name, username, email, password, confirm_password]):
        return render_template("index.html", error="Please fill out all fields")


    if password != confirm_password:
        return render_template("index.html", error="Passwords do not match!")
    
    if Admin.query.filter_by(username=username).first():
        return render_template("index.html", error="User already exists!")
    
    if Admin.query.filter_by(email =email).first():
        return render_template("index.html", error="Email already exists!")
   
    new_admin= Admin(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email
    )
   
    new_admin.set_password(password)
    db.session.add(new_admin)
    db.session.commit()
    
    session['username']=username
    return redirect(url_for('dashboard'))
\



# database model for website content
class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    published= db.Column(db.Boolean, default=False)


#dashboard route
@app.route("/dashboard")
def dashboard():
    if "username" in session:
        content_list = Content.query.all()  # fetch all content
        return render_template("dashboard.html", content=content_list)
    else:
        return redirect(url_for("home"))


#get all the contents on the website
@app.route("/get_content", methods=["GET"])
def get_content():
    if "username" in session:
        content_list = Content.query.filter_by(published=True).all()
        content_data = [{"id": item.id, "title": item.title, "body": item.body, "published": item.published} for item in content_list]
        return {"content": content_data}
    return redirect(url_for("home"))

#get all contents from the preview page
@app.route("/get_all_content", methods=["GET"])
def get_all_content():
    if "username" in session:
        content_list = Content.query.all()
        content_data = [{"id": item.id, "title": item.title, "body": item.body, "published": item.published} for item in content_list]
        return {"content": content_data}
    return redirect(url_for("home"))

#publish content
@app.route("/publish_content/<int:id>", methods=["POST"])
def publish_content(id):
    if "username" in session:
        item = Content.query.get_or_404(id)
        item.published = True  # Always publish
        db.session.commit()
        return "OK"  # simple response for fetch
    return "Unauthorized", 403



# Add new content
@app.route("/add_content", methods=["POST"])
def add_content():
    if "username" in session:
        title = request.form.get("title")
        body = request.form.get("body")
        

        if title and body:
            new_item = Content(title=title, body=body)
            db.session.add(new_item)
            db.session.commit()
        return redirect(url_for("dashboard"))
    return redirect(url_for("home"))

#to edit the contents
@app.route("/edit_content/<int:id>", methods=["POST"])
def edit_content(id):
    if "username" in session:
        content = Content.query.get_or_404(id)  # get content by ID or return 404
        title = request.form.get("title")
        body = request.form.get("body")

        if title and body:
            content.title = title
            content.body = body
            db.session.commit()
        
        return redirect(url_for("dashboard"))
    return redirect(url_for("home"))

#to delete the contents

@app.route("/delete_content/<int:id>", methods=["POST"])
def delete_content(id):
    if "username" in session:
        content = Content.query.get_or_404(id)
        db.session.delete(content)
        db.session.commit()
        return redirect(url_for("dashboard"))
    return redirect(url_for("home"))

#logout route


@app.route("/logout")
def logout():
    session.pop("username", None)  # remove the logged-in user from session
    return redirect(url_for("home"))  # redirect to the login/home page





if __name__ == "__main__":
    with app.app_context():
       db.create_all()
    app.run(debug=True, port=5001)
