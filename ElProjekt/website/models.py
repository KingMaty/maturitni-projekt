from flask_sqlalchemy import SQLAlchemy
from website import app

db = SQLAlchemy(app)

class Student(db.Model):
    student_id = db.Column(db.Integer, primary_key=True)
    student_email = db.Column(db.String(255), unique=True, nullable=False)

class Teacher(db.Model):
    teacher_id = db.Column(db.Integer, primary_key=True)
    teacher_name = db.Column(db.String(255), nullable=False)
    teacher_email = db.Column(db.String(255), unique=True, nullable=False)

class Subject(db.Model):
    subject_id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(255), nullable=False)

class TeacherSubject(db.Model):
    teacher_subject_id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.subject_id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.teacher_id'), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('subject_id', 'teacher_id', 'academic_year'),)

class Question(db.Model):
    question_id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.subject_id'), nullable=False)
    teacher_subject_id = db.Column(db.Integer, db.ForeignKey('teacher_subject.teacher_subject_id'), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)

class Answer(db.Model):
    answer_id = db.Column(db.Integer, primary_key=True)
    answer_text = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.question_id'), nullable=False)
    session_id = db.Column(db.String(255), nullable=False)
    __table_args__ = (db.UniqueConstraint('question_id', 'session_id'),)

class Enrollment(db.Model):
    enrollment_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    teacher_subject_id = db.Column(db.Integer, db.ForeignKey('teacher_subject.teacher_subject_id'), nullable=False)
    academic_year = db.Column(db.Integer, nullable=False)
