"""Prüft die verbindlichen Komponentengrenzen ohne Anwendungscode auszuführen."""

import ast
import sys
from pathlib import Path

# Erlaubte Komponentenimporte: Fachkern mit eigenen Ports, konkrete Adapter
# ausserhalb der Domänen; Verdrahtung ausschliesslich in app.bootstrap.
ALLOWED = {
    "app.web": {
        "app.domains.users",
        "app.domains.devices",
        "app.domains.repairs",
        "app.domains.parts",
    },
    "app.adapters.users": {"app.domains.users"},
    "app.api": {"app.domains.users", "app.domains.repairs"},
    "app.domains.users": set(),
    "app.domains.devices": set(),
    "app.domains.repairs": {"app.domains.costs"},
    "app.domains.parts": {"app.domains.costs"},
    "app.domains.costs": set(),
    "app.data": {
        "app.domains.users",
        "app.domains.devices",
        "app.domains.repairs",
        "app.domains.parts",
    },
}
DATABASE_LIBRARIES = {"sqlalchemy", "flask_sqlalchemy", "psycopg", "psycopg2", "sqlite3"}
TECHNICAL_MODULES = {"app", "app.bootstrap", "app.config", "app.extensions", "app.diagnostics"}


def component(module: str) -> str | None:
    return next((name for name in ALLOWED if module == name or module.startswith(name + ".")), None)


# Nur tatsächlich gemeinsam benötigte fachliche Typen liegen ausserhalb der Slices.
DOMAIN_SHARED = {"ports", "dto", "model", "errors"}


def domain_member(module: str, domain: str) -> str | None:
    relative = module.removeprefix(domain + ".")
    return relative.split(".")[0] if module != domain else None


def is_contract(target: str, domain: str) -> bool:
    parts = target.removeprefix(domain + ".").split(".")
    # Domänenweit oder direkt im Anwendungsfall, niemals beliebig tief in Adaptern.
    return parts[0] in {"ports", "dto"} or (
        len(parts) >= 2 and parts[0] not in DOMAIN_SHARED and parts[1] in {"ports", "dto"}
    )


def imports(tree: ast.AST, module: str, is_package: bool) -> list[tuple[int, str]]:
    """Normalisiert auch relative Imports und `from app import data`."""
    found = []
    package = module if is_package else module.rpartition(".")[0]
    # Auch Imports in Funktionen und TYPE_CHECKING-Blöcken sind Abhängigkeiten;
    # die Analyse führt dafür keinen Anwendungscode aus.
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                # Ein Punkt bezeichnet das aktuelle Paket, jeder weitere dessen
                # Elternpaket; __init__.py hat deshalb eine andere Basis als Module.
                parents = package.split(".")
                base = ".".join(parents[: len(parents) - node.level + 1] + ([base] if base else []))
            for alias in node.names:
                found.append((node.lineno, base + "." + alias.name))
    return found


def check_source(source: str, module: str, *, is_package: bool = False) -> list[str]:
    tree = ast.parse(source)
    origin = component(module)
    errors = []
    if (
        origin is None
        and module not in TECHNICAL_MODULES
        and module not in {"app.domains", "app.adapters"}
    ):
        errors.append(f"{module}: nicht zugeordnete technische oder fachliche Komponente")

    for line, target in imports(tree, module, is_package):
        destination = component(target)
        reason = None
        if target == "flask_security.views" or target.startswith("flask_security.views."):
            reason = "Benutzerabläufe müssen über injizierte Handler statt Bibliotheks-Views laufen"
        elif origin and (
            target.split(".")[0] == "importlib"
            or target in {"builtins.__import__", "builtins.eval", "builtins.exec"}
        ):
            reason = "dynamische Imports umgehen die überprüfbaren Modulgrenzen"
        elif module in {
            "app.config",
            "app.extensions",
            "app.domains",
            "app.adapters",
        } and target.startswith("app"):
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
        elif (
            origin
            and origin.startswith("app.domains.")
            and (target.split(".")[0] not in sys.stdlib_module_names | {"app", "__future__"})
        ):
            reason = "Fachkomponenten dürfen keine Framework-/Infrastrukturbibliothek importieren"
        elif origin in {"app.data", "app.adapters.users"} and destination and destination != origin:
            if not is_contract(target, destination):
                reason = "Adapter dürfen nur Domain-Ports und DTOs importieren"
        # Die Komponententabelle allein erlaubt noch jede Verbindung innerhalb
        # einer Domäne. Diese zweite Prüfung schützt zusätzlich ihre Slice-Grenzen.
        if not reason and origin and origin.startswith("app.domains.") and destination == origin:
            source_member = domain_member(module, origin)
            target_member = domain_member(target, origin)
            if source_member and target_member not in DOMAIN_SHARED | {source_member}:
                reason = "Anwendungsfälle dürfen keine anderen Slices importieren"
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
