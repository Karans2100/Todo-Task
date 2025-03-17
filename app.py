from flask import Flask, render_template, jsonify, request, redirect, make_response, url_for, session
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail, Message
from dotenv import load_dotenv
import jwt
import jwt.algorithms
import mysql.connector
import requests, os

def decodeJWT():
    token = request.cookies.get("token")
    if(token):
        emailjson = jwt.decode(token, app.secret_key, algorithms="HS256")
        return emailjson["email"]
    return None

# DB Connection
try:
    conn = mysql.connector.connect(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    host=os.getenv("DB_HOST")
    )

    print ("DB Connected")
    cursor = conn.cursor()

    user_table_creation_query = """
    CREATE TABLE IF NOT EXISTS users (
        userId INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        email VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255)
    );
    """

    task_table_creation_query = """
    CREATE TABLE IF NOT EXISTS tasks (
        taskId INT AUTO_INCREMENT PRIMARY KEY,
        task VARCHAR(255) NOT NULL,
        isCompleted BOOLEAN DEFAULT FALSE,
        createdBy INT,
        FOREIGN KEY (createdBy) REFERENCES users(userId)
        ON DELETE CASCADE
        ON UPDATE CASCADE
    );
    """
    
    cursor.execute(user_table_creation_query)
    cursor.execute(task_table_creation_query)

except Exception as e:
    print("DB Connection Error: ", e)

# Creating Flask Application
app = Flask(__name__, template_folder="views")
app.secret_key = "karan"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = os.getenv("MAIL_PORT")
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")
mail = Mail(app)

appConf = {
    "CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
    "CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
    "META_URL": "https://accounts.google.com/.well-known/openid-configuration",
    "PORT": os.getenv("APP_PORT")
}
CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"

oauth = OAuth(app)
oauth.register("TodoApp", client_id=appConf.get("CLIENT_ID"), client_secret=appConf.get("CLIENT_SECRET"), server_metadata_url=appConf.get("META_URL"), client_kwargs={
    "scope": "openid profile email"
})


@app.route("/", methods=["GET"])
def get_home():
    email = decodeJWT()
    if(email):
        check_email_query = """
        SELECT * FROM users WHERE email = (%s);
        """
        cursor.execute(check_email_query, (email,))
        result = cursor.fetchall()
        if(len(result) == 1):
            return render_template("todo.html")
        else:
            return redirect("/login")
    else:
        return redirect("/login")
    
        

@app.route("/register", methods=["GET"])
def get_register():
    return render_template("register.html")

@app.route("/login", methods=["GET"])
def get_login():
    return render_template("login.html")

@app.route("/api/register", methods=["POST"])
def register_user():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    check_email_query = """
    SELECT * FROM users WHERE email = (%s);
    """
    cursor.execute(check_email_query, (email,))
    result = cursor.fetchall()
    
    if(len(result) == 0):
        register_user_query = """
        INSERT INTO users (name, email, password) VALUES (%s, %s, %s);
        """
        cursor.execute(register_user_query, (name, email, password))
        conn.commit()

        token = jwt.encode({"email": email}, app.secret_key, algorithm="HS256")
        resp = make_response({"status": "User Created Successfully!", "code": 201})
        resp.set_cookie("token", token)
        return resp
    else:
        return {"status": "User Already Exists!", "code": 409}

@app.route("/api/login", methods=["POST"])
def login_user():
    email = request.form.get("email")
    password = request.form.get("password")
    login_user_query = """
    SELECT * FROM users WHERE email = (%s)  AND password = (%s);
    """
    cursor.execute(login_user_query, (email, password))
    result = cursor.fetchall()

    if(len(result) == 1):
        token = jwt.encode({"email": email}, app.secret_key, algorithm="HS256")
        resp = make_response({"status": "Log In Successfully!", "code": 200})
        resp.set_cookie("token", token)
        return resp
    else:
        return {"status": "Wrong Email or Password! Try Again", "code": 409}

@app.route("/api/logout", methods=["GET"])
def logout_user():
    resp = make_response("Cookie Deleted")
    resp.delete_cookie("token")
    return resp


@app.route("/api/task", methods=["GET"])
def get_tasks():
    email = decodeJWT()
    if email:
        get_tasks_query = """
        SELECT * FROM tasks WHERE createdBy = (SELECT userId FROM users WHERE email = (%s));
        """
        cursor.execute(get_tasks_query, (email,))
        result = cursor.fetchall()
        return jsonify(result)
    else:
        return redirect("/login")

@app.route("/api/task", methods=["POST"])
def add_task():
    task = request.form.get("task")
    email = decodeJWT()

    if email:
        get_userId_query = """
        SELECT userId FROM users WHERE email = (%s);
        """
        cursor.execute(get_userId_query, (email,))
        userId = cursor.fetchall()[0][0]

        if not userId:
            return redirect("/login")

        add_task_query = """
        INSERT INTO tasks (task, createdBy) VALUES (%s, %s);
        """
        cursor.execute(add_task_query, (task, userId))
        conn.commit()

        # Sending email
        msg = Message("Task Created", recipients=[email])
        msg.body = f"You have created a new task: {task}"

        try:
            mail.send(msg)
            print("Email sent")
        except Exception as e:
            print("Mail Sending Error: ", e)

        return redirect("/")
    else:
        return redirect("/login")

@app.route("/api/task/<int:id>", methods=["PATCH"])
def update_task(id):
    update_task_query = """
    UPDATE tasks SET isCompleted = NOT isCompleted WHERE taskId = (%s)
    """
    try:
        cursor.execute(update_task_query, (id,))
        conn.commit()
    except Exception as e:
        print("Updating Task Error: ", e)
    
    return render_template("todo.html")


@app.route("/api/task/<int:id>", methods=["DELETE"])
def delete_task(id):
    delete_task_query = """
    DELETE FROM tasks WHERE taskId = (%s)
    """
    try:
        cursor.execute(delete_task_query, (id,))
        conn.commit()
    except Exception as e:
        print("Deleting Task Error: ", e)
        
    return render_template("todo.html")


# Log in for google
@app.route("/login/google")
def google_login():
    return oauth.todo.authorize_redirect(redirect_uri=f"http://localhost:{os.getenv("APP_PORT")}/callback", _external=True)

@app.route("/callback")
def callback():
    oauth_token = oauth.todoc.authorize_access_token()
    # print(token)

    public_key = None
    certs = requests.get(CERTS_URL).json()
    decoded_header = jwt.get_unverified_header(oauth_token["id_token"])
    for key in certs["keys"]:
        if key["kid"] == decoded_header["kid"]:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            break

    result = jwt.decode(oauth_token["id_token"], public_key, algorithms=["RS256"], audience=appConf.get("CLIENT_ID"))
    email = result["email"]
    name = result["given_name"]

    check_email_query = """
    SELECT * FROM users WHERE email = (%s);
    """
    cursor.execute(check_email_query, (email,))
    result = cursor.fetchall()
    
    if(len(result) == 0):
        register_user_query = """
        INSERT INTO users (name, email) VALUES (%s, %s);
        """
        cursor.execute(register_user_query, (name, email))
        conn.commit()

        token = jwt.encode({"email": email}, app.secret_key, algorithm="HS256")
        resp = make_response(redirect("/"))
        resp.set_cookie("token", token)
        return resp
    else:
        token = jwt.encode({"email": email}, app.secret_key, algorithm="HS256")
        resp = make_response(redirect("/"))
        resp.set_cookie("token", token)
        return resp
    

if __name__ == "__main__":
    app.run(debug=True)