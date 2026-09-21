"""Startseite mit Einstieg in die persönliche Reparaturverwaltung."""

from flask import render_template

from app.web import blueprint


@blueprint.get("/")
def index():
    return render_template("index.html")
