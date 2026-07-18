from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    PasswordField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
)


class LoginForm(FlaskForm):
    email = StringField(
        validators=[
            DataRequired(),
            Email(),
            Length(max=320),
        ],
    )

    password = PasswordField(
        validators=[
            DataRequired(),
            Length(min=1, max=128),
        ],
    )

    remember_me = BooleanField()
    submit = SubmitField()


class RegisterForm(FlaskForm):
    full_name = StringField(
        validators=[
            DataRequired(),
            Length(min=2, max=120),
        ],
    )

    organization_name = StringField(
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

    password = PasswordField(
        validators=[
            DataRequired(),
            Length(min=12, max=128),
        ],
    )

    password_confirmation = PasswordField(
        validators=[
            DataRequired(),
            EqualTo("password"),
        ],
    )

    submit = SubmitField()