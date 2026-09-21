# Isolierter Deployment-Testhost; enthält keine Host-Docker-Socket-Freigabe.
FROM docker:29.6.1-dind@sha256:66d292e5c26bd33a6f6f61cacb880de2186339a524ecba1ce098dbbaceed6515
RUN apk del openssh-client \
    && apk add --no-cache openssh-server python3 sudo \
    && adduser -D -s /bin/sh repairhub-deploy \
    && addgroup repairhub-deploy docker \
    && passwd -d repairhub-deploy \
    && printf 'repairhub-deploy ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/repairhub-test \
    && chmod 0440 /etc/sudoers.d/repairhub-test \
    && printf 'PasswordAuthentication no\nPermitRootLogin no\n' > /etc/ssh/sshd_config.d/repairhub.conf
COPY entrypoint.sh /test-entrypoint.sh
ENTRYPOINT ["/bin/sh", "/test-entrypoint.sh"]
