"""Prüft die verbindlichen Komponentengrenzen ohne Anwendungscode auszuführen."""

import ast
import sys
from pathlib import Path

# Entspricht RepairHub_02_Komponenten.puml; die versteckte Layoutkante fehlt bewusst.
ALLOWED = {
    "app.web": {
        "app.services.users",
        "app.services.devices",
        "app.services.repairs",
        "app.services.parts",
    },
    "app.api": {"app.services.users", "app.services.repairs"},
    "app.services.users": {"app.data"},
    "app.services.devices": {"app.data"},
    "app.services.repairs": {"app.data", "app.services.costs"},
    "app.services.parts": {"app.data", "app.services.costs"},
    "app.services.costs": set(),
    "app.data": set(),
}
DATABASE_LIBRARIES = {"sqlalchemy", "flask_sqlalchemy", "psycopg", "psycopg2", "sqlite3"}
TECHNICAL_MODULES = {"app", "app.config", "app.extensions", "app.diagnostics"}


def component(module: str) -> str | None:
    return next((name for name in ALLOWED if module == name or module.startswith(name + ".")), None)


def imports(tree: ast.AST, module: str, is_package: bool) -> list[tuple[int, str]]:
    """Normalisiert auch relative Imports und `from app import data`."""
    found = []
    package = module if is_package else module.rpartition(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parents = package.split(".")
                base = ".".join(parents[: len(parents) - node.level + 1] + ([base] if base else []))
            for alias in node.names:
                found.append((node.lineno, base + "." + alias.name))
    return found


def check_source(source: str, module: str, *, is_package: bool = False) -> list[str]:
    tree = ast.parse(source)
    origin = component(module)
    errors = []
    if origin is None and module not in TECHNICAL_MODULES and module != "app.services":
        errors.append(f"{module}: nicht zugeordnete technische oder fachliche Komponente")

    for line, target in imports(tree, module, is_package):
        destination = component(target)
        reason = None
        if origin and (
            target.split(".")[0] == "importlib"
            or target in {"builtins.__import__", "builtins.eval", "builtins.exec"}
        ):
            reason = "dynamische Imports umgehen die überprüfbaren Modulgrenzen"
        elif module in {"app.config", "app.extensions", "app.services"} and target.startswith(
            "app"
        ):
            reason = "technische Initialisierung darf keine Fachkomponenten nachladen"
        elif (
            module == "app.diagnostics"
            and target.startswith("app.")
            and target != ("app.data.health.database_ready")
        ):
            reason = "Diagnoseschnittstelle darf nur die technische Datenbankprüfung verwenden"
        elif (
            origin and destination and origin != destination and destination not in ALLOWED[origin]
        ):
            reason = "unerlaubte fachliche Abhängigkeit"
        elif origin and target.startswith("app.") and destination is None:
            # Technische Ausnahmen sind absichtlich symbolgenau, keine Hintertür über db.
            allowed_technical = (
                origin == "app.web" and target == "app.diagnostics.check_readiness"
            ) or (origin == "app.data" and target == "app.extensions.db")
            if not allowed_technical:
                reason = "unerlaubter technischer Umweg oder Sammelimport"
        elif origin and target == "app":
            reason = "Sammelimport der Application Factory"
        elif origin != "app.data" and origin and target.split(".")[0] in DATABASE_LIBRARIES:
            reason = "Datenbankbibliothek ausserhalb des Datenzugriffs"
        elif origin == "app.services.costs" and target.split(".")[0] in {
            "flask",
            "flask_login",
            "flask_wtf",
            "flask_migrate",
        }:
            reason = "Kostenberechnung muss unabhängig von Flask bleiben"
        elif origin == "app.data" and destination and destination != origin:
            reason = "Datenzugriff darf keine höhere Schicht importieren"
        if reason:
            errors.append(f"{module}:{line}: {reason}: {target}")

    # Dynamische Imports könnten die überprüfbare Abhängigkeitsstruktur umgehen.
    if origin:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else None
                attribute = node.func.attr if isinstance(node.func, ast.Attribute) else None
                if name in {"__import__", "eval", "exec"} or attribute == "import_module":
                    errors.append(f"{module}:{node.lineno}: dynamische Code-/Modulladung")
    return errors


def check_project(root: Path) -> list[str]:
    errors = []
    for name in ALLOWED:
        if not (root / name.replace(".", "/") / "__init__.py").is_file():
            errors.append(f"{name}: verbindliche Paketgrenze fehlt")
    for path in sorted((root / "app").rglob("*.py")):
        relative = path.relative_to(root).with_suffix("")
        module = ".".join(relative.parts)
        is_package = path.name == "__init__.py"
        if is_package:
            module = module.removesuffix(".__init__")
        errors.extend(check_source(path.read_text(), module, is_package=is_package))
    return errors


if __name__ == "__main__":
    violations = check_project(Path(__file__).resolve().parents[1])
    for violation in violations:
        print(violation, file=sys.stderr)
    if violations:
        raise SystemExit(1)
    print("Komponentengrenzen geprüft: keine unerlaubten Imports.")
