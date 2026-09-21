"""Veraltete Produktionsläufe abweisen und beide Arten von Release-Tags auflösen."""

import os
import subprocess
from urllib.parse import quote


def remote_commit(repository: str, ref: str) -> str:
    # Der commits-Endpunkt löst auch annotierte Tags bis zum Commit auf; git/ref nicht.
    # Festes gh-Programm mit getrennten Argumenten; keine Auswertung durch eine Shell.
    result = subprocess.run(  # nosec B603,B607
        ["gh", "api", f"repos/{repository}/commits/{quote(ref, safe='')}", "--jq", ".sha"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def check_release(repository: str, ref: str, commit: str, event: str) -> None:
    if event not in {"push", "release"}:
        raise ValueError("Dieses Ereignis darf keine Produktion ausliefern.")
    if not ref.startswith("refs/tags/"):
        raise ValueError("Nur Release-Tags dürfen veröffentlichen.")
    # Erneut gegen den aktuellen Remote-Stand prüfen: Ein wartender CI-Lauf kann
    # inzwischen veraltet sein, obwohl seine vorherigen Prüfungen erfolgreich waren.
    if remote_commit(repository, "refs/heads/main") != commit:
        raise ValueError(
            "Veralteter oder fremder Release: Commit ist nicht der aktuelle main-Stand."
        )
    if remote_commit(repository, ref) != commit:
        raise ValueError("Release-Tag verweist nicht mehr auf den geprüften Commit.")


if __name__ == "__main__":
    check_release(
        os.environ["GITHUB_REPOSITORY"],
        os.environ["GITHUB_REF"],
        os.environ["GITHUB_SHA"],
        os.environ["GITHUB_EVENT_NAME"],
    )
