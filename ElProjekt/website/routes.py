import datetime
import requests
from flask import redirect, url_for, render_template, request, session, Blueprint
from functools import wraps
from website import app, mysql
from website import auth
from website.models import TeacherSubject, db, Question, Answer
from website.forms import QuestionForm, AnswerForm
from website.auth import OAUTH2_PROVIDERS, get_user_info

routes = Blueprint('routes', __name__)

def get_current_academic_year():
    current_date = datetime.datetime.now()
    if current_date.month < 9:
        return current_date.year - 1
    else:
        return current_date.year

current_academic_year = get_current_academic_year()

@routes.route('/login')
def login():
    authorization_url = 'https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={}&redirect_uri={}&scope=email'.format(
        OAUTH2_PROVIDERS['google']['client_id'],
        url_for('routes.authorize', _external=True)
    )
    return redirect(authorization_url)

@routes.route('/')
def index():
    cursor = mysql.get_db().cursor()
    cursor.execute("SELECT * FROM your_table_name")
    data = cursor.fetchall()
    return render_template('index.html', data=data)

@routes.route('/add', methods=['POST'])
def add():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cursor = mysql.get_db().cursor()
        cursor.execute("INSERT INTO your_table_name (name, email) VALUES (%s, %s)", (name, email))
        mysql.get_db().commit()
        return redirect(url_for('routes.index'))

def role_required(role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if session.get('role') != role:
                return redirect(url_for('routes.unauthorized'))
            return func(*args, **kwargs)
        return wrapper
    return decorator

@routes.route('/active_questions')
def active_questions():
    current_year = datetime.datetime.now().year
    active_questions = Question.query.filter_by(year=current_year).all()
    return render_template('active_questions.html', questions=active_questions)

@routes.route('/answers')
def answers():
    current_year = datetime.datetime.now().year
    previous_years_questions = Question.query.filter(Question.year < current_year).all()
    return render_template('answers.html', questions=previous_years_questions)

@routes.route('/add_question', methods=['GET', 'POST'])
@role_required('teacher')  
def add_question():
    form = QuestionForm()
    teacher_subjects = TeacherSubject.query.filter_by(academic_year=current_academic_year).all()
    form.teacher_subject.choices = [(ts.id, ts.subject_name) for ts in teacher_subjects]
    if form.validate_on_submit():
        question_text = form.text.data
        academic_year = datetime.datetime.now().year
        teacher_subject_id = form.teacher_subject.data
        new_question = Question(text=question_text, teacher_subject_id=teacher_subject_id)
        new_question.academic_year = current_academic_year
        db.session.add(new_question)
        db.session.commit()
        return redirect(url_for('routes.index'))
    return render_template('add_question.html', form=form)

@routes.route('/add_answer', methods=['GET', 'POST'])
@role_required('student')  
def submit_answers():
    if request.method == 'POST':
        student_id = session['user_id']
        for key, value in request.form.items():
            if key.startswith('answer'):
                question_id = int(key.replace('answer', ''))
                existing_answer = Answer.query.filter_by(question_id=question_id, student_id=student_id).first()
                if existing_answer:
                    continue
                new_answer = Answer(answer_text=value, question_id=question_id, student_id=student_id)
                db.session.add(new_answer)
        db.session.commit()
        return redirect(url_for('routes.active_questions'))
    else:
        return redirect(url_for('routes.index'))

@routes.route('/authorize')
def authorize():
    authorization_code = request.args.get('code')
    token_url = 'https://accounts.google.com/o/oauth2/token'
    payload = {
        'code': authorization_code,
        'client_id': auth.GOOGLE_CLIENT_ID,
        'client_secret': auth.GOOGLE_CLIENT_SECRET,
        'redirect_uri': 'your_redirect_uri',
        'grant_type': 'authorization_code'
    }
    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        access_token = response.json().get('access_token')
        user_info = get_user_info(access_token)
        if user_info:
            session['user_info'] = user_info
            return redirect(url_for('routes.index'))
        else:
            return 'Failed to retrieve user information', 500
    else:
        return 'Failed to exchange authorization code for access token', 500
