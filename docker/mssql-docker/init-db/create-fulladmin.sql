-- init-db/create-fulladmin.sql

CREATE LOGIN ${FULLADMIN_USER} WITH PASSWORD = '${FULLADMIN_PASSWORD}';
ALTER SERVER ROLE sysadmin ADD MEMBER ${FULLADMIN_USER};
GO