#!/bin/sh
set -eu

# Schlüssel kommen erst zur Testlaufzeit, nie ins Testhost-Image.
install -d -m 0700 -o repairhub-deploy -g repairhub-deploy /home/repairhub-deploy/.ssh
install -m 0600 -o repairhub-deploy -g repairhub-deploy \
  /test-access/authorized_keys /home/repairhub-deploy/.ssh/authorized_keys
ssh-keygen -A
# Nur Unix-Socket im isolierten Container; kein offener Docker-TCP-Endpunkt.
dockerd --host=unix:///var/run/docker.sock --group=docker > /tmp/dockerd.log 2>&1 &
exec /usr/sbin/sshd -D -e
