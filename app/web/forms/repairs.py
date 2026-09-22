from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, TextAreaField


class DescriptionForm(FlaskForm):
    description = TextAreaField(_("Fault description"))


class StatusForm(FlaskForm):
    status = SelectField(
        _("Repair status"),
        choices=[
            ("open", _("Open")),
            ("in_progress", _("In progress")),
            ("completed", _("Completed")),
        ],
    )


class StepForm(FlaskForm):
    description = TextAreaField(_("Step description"))
    completed = BooleanField(_("Done"))
