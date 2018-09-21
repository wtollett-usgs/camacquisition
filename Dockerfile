FROM python:3.7

RUN apt-get update && apt-get -y install cron imagemagick mencoder tcsh wget

WORKDIR /root/certs
COPY support/DOIRootCA2.cer .

WORKDIR /usr/share/ca-certificates/extra
COPY support/DOIRootCA2.cer DOIRootCA2.crt
RUN echo "extra/DOIRootCA2.crt" >> /etc/ca-certificates.conf && update-ca-certificates

RUN groupadd -g 1500 -r geology \
    && useradd -u 1500 -g geology -s /sbin/nologin geod

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.1.6/supercronic-linux-amd64 \
    SUPERCRONIC=supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=c3b78d342e5413ad39092fd3cfc083a85f5e2b75

RUN curl -fsSLO "$SUPERCRONIC_URL" \
 && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
 && chmod +x "$SUPERCRONIC" \
 && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
 && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

WORKDIR /app/camacquisition
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY support/bin /app/camacquisition/bin

COPY VERSION .

RUN chown -R geod:geology /app/camacquisition
USER geod

CMD ["/usr/local/bin/supercronic", "/app/camacquisition/etc/geod.cron"]