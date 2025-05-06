#!/bin/bash
set -e

# Verify required env vars
if [ -z "$MSSQL_SA_PASSWORD" ]; then
  echo "❌ MSSQL_SA_PASSWORD environment variable not set."
  exit 1
fi

if [ -z "$FULLADMIN_USER" ] || [ -z "$FULLADMIN_PASSWORD" ]; then
  echo "❌ FULLADMIN_USER or FULLADMIN_PASSWORD environment variables not set."
  exit 1
fi

# Start SQL Server in the background
/opt/mssql/bin/sqlservr &

echo "🔍 Waiting for SQL Server to start..."
until /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$MSSQL_SA_PASSWORD" -Q "SELECT 1" &> /dev/null
do
  echo -n "."
  sleep 1
done
echo ""
echo "✅ SQL Server is up and running."

# Find the first .bak file
BAK_FILE=$(ls /var/opt/mssql/backup/*.bak | head -n 1 || true)
if [ -z "$BAK_FILE" ]; then
  echo "❌ No .bak file found in /var/opt/mssql/backup. Exiting."
  exit 1
fi

echo "🔄 Retrieving database name from backup using RESTORE HEADERONLY..."
HEADER_WITH_COLS=$(/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
    -Q "RESTORE HEADERONLY FROM DISK = N'$BAK_FILE'" -h 1 -W -s"|" \
    | grep -v "rows affected" \
    | grep -v '^-*$' || true)

if [ -z "$HEADER_WITH_COLS" ]; then
  echo "❌ Failed to run RESTORE HEADERONLY or no output."
  exit 1
fi

COL_NAMES=$(echo "$HEADER_WITH_COLS" | head -1)
COL_VALUES=$(echo "$HEADER_WITH_COLS" | tail -1)

# Find DatabaseName column index
COL_INDEX=$(echo "$COL_NAMES" | tr '|' '\n' | grep -nx 'DatabaseName' | cut -d':' -f1)
if [ -z "$COL_INDEX" ]; then
    echo "❌ Could not find DatabaseName column in RESTORE HEADERONLY output."
    echo "$HEADER_WITH_COLS"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="TargetDB"
DB_NAME="${DB_NAME}_${TIMESTAMP}"

echo "📄 Found database name from backup: $DB_NAME"

echo "🔄 Retrieving logical file names from backup (FILELISTONLY)..."
FILELIST=$(/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
    -Q "RESTORE FILELISTONLY FROM DISK = N'$BAK_FILE'" -s"|" -W || true)

if [ -z "$FILELIST" ]; then
  echo "❌ Failed to read file list from backup."
  exit 1
fi

DATA_NAME=$(echo "$FILELIST" | grep '|D|' | head -1 | awk -F'|' '{print $1}' | xargs)
LOG_NAME=$(echo "$FILELIST" | grep '|L|' | head -1 | awk -F'|' '{print $1}' | xargs)

if [ -z "$DATA_NAME" ] || [ -z "$LOG_NAME" ]; then
  echo "❌ Could not identify logical data and log files in the backup."
  echo "Filelist output:"
  echo "$FILELIST"
  exit 1
fi

echo "📄 DATA_NAME=$DATA_NAME, LOG_NAME=$LOG_NAME for DB=$DB_NAME"

DATA_FILE="/var/opt/mssql/data/${DB_NAME}_Data.mdf"
LOG_FILE="/var/opt/mssql/data/${DB_NAME}_Log.ldf"

RESTORE_SCRIPT="/tmp/restore_${DB_NAME}.sql"
cat > "$RESTORE_SCRIPT" <<EOF
USE [master];
RESTORE DATABASE [$DB_NAME]
FROM DISK = N'$BAK_FILE'
WITH MOVE N'$DATA_NAME' TO N'$DATA_FILE',
     MOVE N'$LOG_NAME' TO N'$LOG_FILE',
     FILE = 1,
     NOUNLOAD,
     STATS = 5;
GO
EOF

echo "🛠️ Generated restore script:"
cat "$RESTORE_SCRIPT"

# Prepare admin user script by env substitution
for file in /docker-entrypoint-initdb.d/*.sql; do
  cp "$file" "${file}.original"
  envsubst < "${file}.original" > "$file"
done

# Restore the database with -b flag
echo "🛠️ Restoring database $DB_NAME..."
/opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$MSSQL_SA_PASSWORD" -b -i "$RESTORE_SCRIPT"
if [ $? -eq 0 ]; then
  echo "✅ Database $DB_NAME restored successfully."
else
  echo "❌ Failed to restore database $DB_NAME."
  exit 1
fi

# Execute init scripts (like create-fulladmin.sql)
for file in /docker-entrypoint-initdb.d/*.sql; do
  echo "🛠️ Executing $file..."
  /opt/mssql-tools/bin/sqlcmd -S localhost -U SA -P "$MSSQL_SA_PASSWORD" -d $DB_NAME -i "$file"
  if [ $? -eq 0 ]; then
    echo "✅ Executed $file successfully."
  else
    echo "❌ Failed to execute $file."
    exit 1
  fi
done

CONNECTION_STRING="DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost,1433;UID=SA;PWD=$MSSQL_SA_PASSWORD;DATABASE=$DB_NAME;Encrypt=no;TrustServerCertificate=yes"
echo "$CONNECTION_STRING" > "$SHARED_DB_CONNECTION_STRING_FILE"

echo "📄 Connection string written to $SHARED_DB_CONNECTION_STRING_FILE"

# Keep SQL Server running in the foreground
wait