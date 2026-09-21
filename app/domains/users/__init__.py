"""Benutzerverwaltung: frameworkfreie Fachlogik mit injizierten Ports.

Jeder Anwendungsfall besitzt einen eigenen Handler, Eingabe-DTO und Gateway-Port.
Die Handler delegieren die etablierten Identitätsverfahren über diese Ports.
Sie implementieren Passwortprüfung und Tokenverwaltung nicht nochmals selbst.
Keine Flask-, ORM- oder konkreten Adapter-Abhängigkeiten.
"""
