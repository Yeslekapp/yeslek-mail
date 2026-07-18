from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


class DomainForm(FlaskForm):
    domain = StringField(
        validators=[
            DataRequired(),
            Length(min=3, max=253),
            Regexp(
                r"^(?!-)(?:[a-zA-Z0-9-]{1,63}\.)+[a-zA-Z]{2,63}$"
            ),
        ],
    )

    submit = SubmitField()