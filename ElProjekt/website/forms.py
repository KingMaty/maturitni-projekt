from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class QuestionForm(FlaskForm):
    text = StringField('Text otázky', validators=[DataRequired()])
    submit = SubmitField('Přidat')

class AnswerForm(FlaskForm):
    text = StringField('Text odpovědi', validators=[DataRequired()])
    submit = SubmitField('Odpovědět')
