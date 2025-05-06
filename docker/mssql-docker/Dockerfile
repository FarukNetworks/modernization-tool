FROM mcr.microsoft.com/mssql/server:2019-latest

ENV ACCEPT_EULA=Y
USER root

RUN apt-get update && \
    apt-get install -y curl apt-transport-https gnupg gettext-base && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y mssql-tools unixodbc-dev && \
    echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> /etc/profile.d/mssql-tools.sh && \
    chmod +x /etc/profile.d/mssql-tools.sh && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/opt/mssql/backup
RUN mkdir -p /docker-entrypoint-initdb.d
RUN mkdir -p /var/opt/shared && chmod 777 /var/opt/shared

COPY ./drop-database-here/*.bak /var/opt/mssql/backup/
COPY ./init-db/*.sql /docker-entrypoint-initdb.d/

# Set ownership using numeric UID:GID
RUN chown -R 10001:0 /var/opt/mssql/backup /docker-entrypoint-initdb.d /var/opt/shared

COPY ./entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER mssql
EXPOSE 1433
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]