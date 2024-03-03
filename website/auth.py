import os
import pathlib
import requests
from flask import session, abort, redirect, request, Blueprint, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from database import connect, insert_data, delete_data

global_conn = None

auth_bp = Blueprint('auth', __name__, static_folder="static", template_folder="templates")

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

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
            return abort(401)
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
    print(request.args["state"])
    print(session["state"])
    if not session["state"] == request.args["state"]:
        abort(500)

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
    return render_template("home.html", active_page="home")

@auth_bp.route("/answers")
def answers():
    if "google_id" not in session:
        return abort(401)
    else:
        return render_template("answers.html", active_page="myanswers")

@auth_bp.route("/active_questions")
def active_questions():
    if "google_id" not in session:
        return abort(401)
    else:
        return render_template("active_questions.html", active_page="myactive_questions")

@auth_bp.route("/home")
def home():
    if "google_id" not in session:
        return abort(401)
    else:
        return render_template("home.html", active_page="home")

@auth_bp.route("/myindex")
def myindex():
    if "google_id" not in session:
        return abort(401)
    else:
        return render_template("myindex.html", active_page="home")

def get_subjects(cursor):
    query = "SELECT * FROM feedbackapp.subjects;"
    cursor.execute(query)
    return cursor.fetchall()

def get_subjects_by_teacher(cursor, teacher_id):
    query = """SELECT subjects.subject_id, subjects.subject_name, teacher_subjects.academic_year, teacher_subjects.teacher_subject_id 
    FROM feedbackapp.subjects JOIN feedbackapp.teacher_subjects ON subjects.subject_id = teacher_subjects.subject_id WHERE
    teacher_subjects.teacher_id = %s
    """
    cursor.execute(query,(teacher_id,))
    return cursor.fetchall()

@auth_bp.route("/myanswers", methods=["POST", "GET"])
def myanswers():
    if "google_id" not in session:
        return abort(401)

    if "conn" not in session:
        global_conn = connect()

    if global_conn is not None:
        cursor = global_conn.cursor()
        subjects = get_subjects(cursor)

        if request.method == "GET":
            return render_template("myanswers.html", subjects=subjects, active_page="myanswers")

        subject_id = request.form['subject_id']
        query = """ SELECT questions.question_id, questions.question_text, answers.answer_text, questions.academic_year
        FROM feedbackapp.questions JOIN feedbackapp.answers ON questions.question_id = answers.question_id WHERE questions.subject_id = %s
        ORDER BY questions.question_id DESC
        """
        cursor.execute(query, (subject_id,))
        qas = cursor.fetchall()

        query = """ SELECT questions.question_id, questions.question_text, questions.academic_year
        FROM feedbackapp.questions WHERE questions.subject_id = %s
        ORDER BY questions.question_id DESC
        """
        cursor.execute(query, (subject_id,))
        questions = cursor.fetchall()

        return render_template("myanswers.html", subjects=subjects, qas=qas, questions=questions, active_page="myanswers")
    else:
        return render_template("mydbconnerror.html", active_page="myanswers")

def get_student_id(cursor, email):
    query = "SELECT student_id FROM feedbackapp.students WHERE student_email = %s"
    cursor.execute(query, (email,))
    student_id_tuple = cursor.fetchone()
    return int(student_id_tuple[0]) if student_id_tuple else None

def get_teacher_id(cursor, email):
    query = "SELECT teacher_id FROM feedbackapp.teachers WHERE teacher_email = %s"
    cursor.execute(query, (email,))
    teacher_id_tuple = cursor.fetchone()
    return int(teacher_id_tuple[0]) if teacher_id_tuple else None

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

def insert_answer_and_student_question(conn, question_id, answer_text, student_id):
    query = "INSERT INTO feedbackapp.answers (question_id, answer_text) VALUES (%s, %s)"
    data = (question_id, answer_text)
    if insert_data(conn, query, data):
        print("Data inserted successfully!")
    else:
        print("Failed to insert data.")
        return False

    query = "INSERT INTO feedbackapp.student_question (question_id, student_id) VALUES (%s, %s)"
    data = (question_id, student_id)
    if insert_data(conn, query, data):
        print("Data inserted successfully!")
    else:
        print("Failed to insert data.")
        return False
    return True

def get_teacher_subjects(cursor, teacher_id):
    query = """  SELECT subjects.subject_id, subjects.subject_name, teacher_subjects.academic_year, teacher_subjects.teacher_subject_id
    FROM feedbackapp.subjects JOIN feedbackapp.teacher_subjects ON subjects.subject_id = teacher_subjects.subject_id 
    WHERE teacher_subjects.teacher_id = %s ORDER BY teacher_subjects.academic_year DESC
    """
    cursor.execute(query, (teacher_id,))
    return cursor.fetchall()    

def get_teacher_questions(cursor, teacher_id):
    query = """  SELECT questions.question_id, questions.question_text, questions.subject_id, questions.teacher_subject_id, questions.academic_year, teacher_subjects.subject_id,
    teacher_subjects.teacher_id FROM feedbackapp.questions JOIN feedbackapp.teacher_subjects ON questions.teacher_subject_id = teacher_subjects.teacher_subject_id
    WHERE teacher_subjects.teacher_id = %s ORDER BY questions.question_id DESC
    """
    cursor.execute(query, (teacher_id,))
    return cursor.fetchall()   

def delete_question(conn, question_id):
    query ="DELETE FROM feedbackapp.questions WHERE question_id = %s"
    if delete_data(conn, query, (question_id,)):
        print("Data deleted successfully!")
        return True
    else:
        print("Failed to delete data.")
        return None

def insert_new_question(conn, question_text, subject_id, teacher_id):
    query = "SELECT teacher_subjects.teacher_subject_id FROM feedbackapp.teacher_subjects WHERE teacher_subjects.subject_id= %s AND teacher_subjects.teacher_id = %s" 
    cursor = conn.cursor()
    cursor.execute(query, (subject_id, teacher_id,))
    teacher_subject_id_tuple = cursor.fetchone()

    query = """INSERT INTO feedbackapp.questions (question_text, subject_id, teacher_subject_id, academic_year) 
    VALUES (%s, %s, %s, %s)
    """
    data = (question_text, subject_id, teacher_subject_id_tuple[0], 2023)
    if insert_data(conn, query, data):
        print("Data inserted successfully!")
        return True
    else:
        print("Failed to insert data.")
    return None

@auth_bp.route("/add_question", methods = ["POST","GET"])
def add_question():
    if "google_id" not in session:
        return abort(401)

    if "conn" not in session:
        global_conn = connect()

    if global_conn is not None:
        cursor = global_conn.cursor()
        email = session["email"]
        teacher_id = get_teacher_id(cursor, email)
        if teacher_id is not None:
            subjects = get_subjects_by_teacher(cursor, teacher_id)
            questions = get_teacher_questions(cursor, teacher_id)
            if request.method == "GET":
                return render_template("add_question.html", subjects=subjects, questions=questions , active_page="add_question")
            else:
                selected_subject  = None
                for key, value in request.form.items():
                    print(f'Key: {key}, Value: {value}')
                    if (key == "selected_subject"):
                        if value.isdigit():
                            selected_subject = value
                    if (key == "delete_question"):
                        if delete_question(global_conn,value) != None :
                            questions = get_teacher_questions(cursor, teacher_id)
                            return render_template("add_question.html", subjects=subjects, questions=questions , active_page="add_question", deleted_successfuly = 1 ) 
                        else:    
                            return render_template("add_question.html", subjects=subjects, questions=questions , active_page="add_question", deleted_successfuly = 2 ) 
                    if (key == "new_question"):
                        if selected_subject == None :
                            print ("1")
                            return render_template("add_question.html", subjects=subjects, questions=questions , active_page="add_question", select_subject = 1 ) 
                        else:
                            print ("2")
                            if insert_new_question(global_conn, value, selected_subject, teacher_id) != None :
                                print("3")
                                questions = get_teacher_questions(cursor, teacher_id)
                                return render_template("add_question.html", subjects=subjects, questions=questions , active_page="add_question", added_successfully = 1 )     
                            else:
                                print("4")
                                return render_template("add_question.html", subjects=subjects, questions=questions , active_page="add_question", added_successfully = 2 )     
                return render_template("add_question.html", subjects=subjects, questions=questions , active_page="add_question")
    else:
        return render_template("mydbconnerror.html", active_page="add_question")

@auth_bp.route("/myactive_questions", methods=["POST", "GET"])
def myactive_questions():
    if "google_id" not in session:
        return abort(401)

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
                return render_template("myactive_questions.html", questions=questions, teacher_subject_names=teacher_subject_names, active_page="myactive_questions")
            else:
                form_data = request.form
                student_id = get_student_id(cursor, email)
                for question_id, answer_text in form_data.items():
                    if answer_text and int(question_id) > 0:
                        success = insert_answer_and_student_question(global_conn, question_id, answer_text, student_id)
                        if not success:
                            return render_template("mydbconnerror.html")
                return render_template("myindex.html", hlaska="Zapsáno v pořádku", active_page="home")
        else:
            return render_template("mydbconnerror.html", active_page="myactive_questions")
    else:
        return render_template("mydbconnerror.html", active_page="myactive_questions")
