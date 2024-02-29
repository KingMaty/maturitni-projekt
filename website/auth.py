import os
import pathlib
import requests
from flask import session, abort, redirect, request, Blueprint,render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from database import connect, insert_data
import json #unsued imp

global_conn = None

auth_bp = Blueprint('auth', __name__, static_folder="static",template_folder="templates")

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # to allow Http traffic for local dev

GOOGLE_CLIENT_ID = "476358247913-u7m802aipif8nnt7un4o8d46rldre87h.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://localhost:5000/callback"
)


def db_is_connected():
     return

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Authorization required
        else:
            return function()

    return wrapper


@auth_bp.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@auth_bp.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    session["email"] = id_info.get("email")
    
    if session["email"].startswith("x"):
        session["role"] = "student"
    else:
        session["role"] = "teacher"
    
    return redirect("/myindex")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@auth_bp.route("/")
def index():
    return "Nejdříve se přihlašte: <a href='/login'><button>Login</button></a>"

@auth_bp.route("/protected_area")
@login_is_required
def protected_area():
    return render_template("home.html")
    #return f"Hello {session['name']}! <br/>  Email {session['email']}! <br/> <a href='/logout'><button>Logout</button></a>"

@auth_bp.route("/answers")
def answers():
    if "google_id" not in session:
            return abort(401)  # Authorization required
    else:
            return render_template("answers.html")

@auth_bp.route("/active_questions")
def active_questions():
    if "google_id" not in session:
            return abort(401)  # Authorization required
    else:
            return render_template("active_questions.html")

@auth_bp.route("/home")
def home():
    if "google_id" not in session:
            return abort(401)  # Authorization required
    else:
            return render_template("myindex.html")
    
@auth_bp.route("/add_questions")
def add_questions():
    if "google_id" not in session:
            return abort(401)  # Authorization required
    else:
            
            return render_template("add_questions.html")


@auth_bp.route("/myindex")
def myindex():
    if "google_id" not in session:
            return abort(401)  # Authorization required
    else:
            
            return render_template("myindex.html")

def get_subjects(cursor):
    query = "SELECT * FROM feedbackapp.subjects;"
    cursor.execute(query)
    return cursor.fetchall()

@auth_bp.route("/myanswers", methods=["POST", "GET"])
def myanswers():
    if "google_id" not in session:
            return abort(401)  # Authorization required
    
    if "conn" not in session:
        global_conn = connect()

    if global_conn is not None:
        cursor = global_conn.cursor()
        #subjects = []
        #questions = []
        #answers = []
        subjects = get_subjects(cursor)

        if request.method == "GET":  
            return render_template("myanswers.html", subjects = subjects)
        
        subject_id = request.form['subject_id']
        query = """ SELECT questions.question_id, questions.question_text, answers.answer_text, questions.academic_year 
        FROM feedbackapp.questions JOIN feedbackapp.answers ON questions.question_id = answers.question_id WHERE questions.subject_id = %s
        ORDER BY questions.question_id ASC
        """
        cursor.execute(query, (subject_id,))
        qas = cursor.fetchall()

        query = """ SELECT questions.question_id, questions.question_text
        FROM feedbackapp.questions WHERE questions.subject_id = %s
        ORDER BY questions.question_id ASC
        """
        cursor.execute(query, (subject_id,))
        questions = cursor.fetchall()

        return render_template("myanswers.html", subjects = subjects, qas = qas, questions = questions )   
    else:
        return render_template("mydbconnerror.html")

def get_student_id(cursor, email):
    query = "SELECT student_id FROM feedbackapp.students WHERE student_email = %s"
    cursor.execute(query, (email,))
    student_id_tuple = cursor.fetchone()
    return int(student_id_tuple[0]) if student_id_tuple else None

def get_teacher_subject_ids(cursor, student_id):
    query = "SELECT teacher_subject_id FROM feedbackapp.enrollments WHERE student_id = %s"
    cursor.execute(query, (student_id,))
    return [int(row[0]) for row in cursor.fetchall()]

def get_teacher_names(cursor):
    query = "SELECT teacher_subjects.teacher_subject_id, teachers.teacher_name FROM feedbackapp.teachers JOIN feedbackapp.teacher_subjects ON teachers.teacher_id = teacher_subjects.teacher_id"
    cursor.execute(query)
    return {int(row[0]): row[1] for row in cursor.fetchall()}

def get_filtered_questions(cursor, student_id):
    query = "SELECT question_id FROM feedbackapp.student_question WHERE student_id = %s"
    cursor.execute(query, (student_id,))
    filtered_questions = [row[0] for row in cursor.fetchall()]

    query = """
        SELECT questions.question_id, questions.question_text, questions.teacher_subject_id, questions.academic_year, subjects.subject_name 
        FROM feedbackapp.questions JOIN feedbackapp.subjects ON questions.subject_id = subjects.subject_id 
        WHERE questions.teacher_subject_id IN (%s)
    """
    cursor.execute(query, (', '.join(map(str, get_teacher_subject_ids(cursor, student_id))),))
    questions = cursor.fetchall()

    return [question for question in questions if question[0] not in filtered_questions]

def insert_answer_and_student_question(cursor, global_conn, question_id, answer_text, student_id):
    query = "INSERT INTO feedbackapp.answers (question_id, answer_text) VALUES (%s, %s)"
    data = (question_id,answer_text)
    if insert_data(global_conn, query, data):
        print("Data inserted successfully!")
    else:
        print("Failed to insert data.")
        return False
    
    query = "INSERT INTO feedbackapp.student_question (question_id, student_id) VALUES (%s, %s)"
    data = (question_id,student_id)
    if insert_data(global_conn, query, data):
        print("Data inserted successfully!")
    else:
        print("Failed to insert data.")
        return False
    return True

@auth_bp.route("/myactive_questions", methods=["POST", "GET"])
def myactive_questions():
    if "google_id" not in session:
        return abort(401)  # Authorization required

    if "conn" not in session:
        global_conn = connect()

    if global_conn is not None:
        cursor = global_conn.cursor()
        email = session["email"]
        student_id = get_student_id(cursor, email)

        if student_id is not None:
            if request.method == "GET":
                teacher_subject_names = get_teacher_names(cursor)
                questions = get_filtered_questions(cursor, student_id)
                return render_template("myactive_questions.html", questions=questions, teacher_subject_names=teacher_subject_names)
            else:
                form_data = request.form
                student_id = get_student_id(cursor, email)
                for question_id, answer_text in form_data.items():
                    if answer_text and int(question_id) > 0:
                        success = insert_answer_and_student_question(cursor, global_conn, question_id, answer_text, student_id)
                        if not success:
                            return render_template("mydbconnerror.html")
                return render_template("myindex.html", hlaska="Zapsáno v pořádku")
        else:
            return render_template("mydbconnerror.html")
    else:
        return render_template("mydbconnerror.html")
    
