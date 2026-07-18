from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class SenderForm(FlaskForm):
    name = StringField(
        validators=[
            DataRequired(),
            Length(min=2, max=160),
        ],
    )

    email = StringField(
        validators=[
            DataRequired(),
            Email(),
            Length(max=320),
        ],
    )

    submit = SubmitField()