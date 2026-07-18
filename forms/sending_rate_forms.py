from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class SendingRateForm(FlaskForm):
    emails_per_minute = IntegerField(
        validators=[
            DataRequired(),
            NumberRange(min=1, max=100000),
        ],
    )

    emails_per_hour = IntegerField(
        validators=[
            DataRequired(),
            NumberRange(min=1, max=10000000),
        ],
    )

    emails_per_domain_per_minute = IntegerField(
        validators=[
            DataRequired(),
            NumberRange(min=1, max=100000),
        ],
    )

    warmup_enabled = BooleanField()
    submit = SubmitField()