"""Gepinnte Galaxy-Collections mit begrenzten Wiederholungen installieren."""

import subprocess
import time


def install() -> int:
    command = [
        "ansible-galaxy",
        "collection",
        "install",
        "-r",
        "deploy/ansible/requirements.yml",
    ]
    for attempt in range(1, 4):
        print(f"Ansible Galaxy: Installationsversuch {attempt}/3", flush=True)
        try:
            result = subprocess.run(command, check=False, timeout=180)
            if result.returncode == 0:
                return 0
        except subprocess.TimeoutExpired:
            print("Ansible Galaxy: Zeitlimit von 180 Sekunden erreicht.", flush=True)
        # Auch nach einem Teil-Download prüft Galaxy erneut die gepinnten Versionen.
        # Keine Zertifikatsausnahme und kein grüner Status nach ausgeschöpften Versuchen.
        if attempt < 3:
            time.sleep(5 if attempt == 1 else 15)
    print("Ansible Galaxy: Installation nach drei Versuchen fehlgeschlagen.", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(install())
