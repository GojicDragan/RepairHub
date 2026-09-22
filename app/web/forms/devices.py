from flask_babel import lazy_gettext as _
from flask_wtf import FlaskForm
from wtforms import StringField


class DeviceForm(FlaskForm):
    name = StringField(_("Device name"))
    manufacturer = StringField(_("Manufacturer"))
    model = StringField(_("Model"))
