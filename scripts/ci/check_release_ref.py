"""Reject stale production runs and resolve lightweight or annotated release tags."""

import os
import subprocess
from urllib.parse import quote


def remote_commit(repository: str, ref: str) -> str:
    # The commits endpoint peels annotated tags to their commit, unlike git/ref.
    # Fixed gh executable with separate arguments; no shell evaluation.
    result = subprocess.run(  # nosec B603,B607
        ["gh", "api", f"repos/{repository}/commits/{quote(ref, safe='')}", "--jq", ".sha"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def check_release(repository: str, ref: str, commit: str, event: str) -> None:
    if event not in {"push", "release", "workflow_dispatch"}:
        raise ValueError("Dieses Ereignis darf keine Produktion ausliefern.")
    if ref != "refs/heads/main" and not ref.startswith("refs/tags/"):
        raise ValueError("Nur main und Release-Tags dürfen veröffentlichen.")
    if remote_commit(repository, "refs/heads/main") != commit:
        raise ValueError(
            "Veralteter oder fremder Release: Commit ist nicht der aktuelle main-Stand."
        )
    if ref.startswith("refs/tags/") and remote_commit(repository, ref) != commit:
        raise ValueError("Release-Tag verweist nicht mehr auf den geprüften Commit.")


if __name__ == "__main__":
    check_release(
        os.environ["GITHUB_REPOSITORY"],
        os.environ["GITHUB_REF"],
        os.environ["GITHUB_SHA"],
        os.environ["GITHUB_EVENT_NAME"],
    )
