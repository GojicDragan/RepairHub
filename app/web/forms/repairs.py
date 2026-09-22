from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import BooleanField, SelectField, StringField, TextAreaField


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


class WorkForm(FlaskForm):
    hours = StringField(_("Working hours"))
    hourly_rate = StringField(_("Hourly rate (CHF)"))


class PartForm(FlaskForm):
    name = StringField(_("Part name"))
    unit_price = StringField(_("Unit price (CHF)"))
    quantity = StringField(_("Quantity"))
