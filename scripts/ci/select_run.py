"""Doppelte Push-Prüfungen bei offenem Pull Request vermeiden."""

import json
import os
import subprocess
from pathlib import Path


def should_run(event: str, repository: str, ref: str) -> bool:
    # Releases, manuelle Aufrufe und PR-Mergeprüfungen bleiben eigenständige Läufe.
    # main wird auch geprüft, falls davon ausnahmsweise ein PR ausgeht.
    if event != "push" or ref == "refs/heads/main":
        return True
    if not ref.startswith("refs/heads/"):
        return True
    branch = ref.removeprefix("refs/heads/")
    owner = repository.split("/", 1)[0]
    result = subprocess.run(  # nosec B603,B607
        [
            "gh",
            "api",
            f"repos/{repository}/pulls",
            "--method",
            "GET",
            "-f",
            "state=open",
            "-f",
            f"head={owner}:{branch}",
            "--paginate",
            "--slurp",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Gleiche Branchnamen in Forks dürfen keinen lokalen Push unterdrücken.
    # API-Fehler brechen die Vorprüfung ab, statt unbemerkt Prüfungen auszulassen.
    pages = json.loads(result.stdout)
    return not any(
        pr["state"] == "open"
        and pr["head"]["ref"] == branch
        and (pr["head"]["repo"] or {}).get("full_name") == repository
        for page in pages
        for pr in page
    )


def main():
    run = should_run(
        os.environ["GITHUB_EVENT_NAME"], os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_REF"]
    )
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"run_checks={str(run).lower()}\n")
    print("Prüfungen ausführen." if run else "Offener PR übernimmt die Prüfungen dieses Branches.")


if __name__ == "__main__":
    main()
