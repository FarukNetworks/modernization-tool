import os
import pyodbc
import json

# Get Each procedure dependencies
procedure_dependencies = []

# New list to store object creation scripts
object_create_scripts = []


# Add code to collect all database objects for object_create_scripts.json
def get_object_definition(object_name, object_type):
    """Get the CREATE script for a database object"""
    try:
        cursor.execute(
            f"SELECT OBJECT_DEFINITION(OBJECT_ID('{object_name}')) AS definition"
        )
        result = cursor.fetchone()
        return result.definition if result and result.definition else None
    except:
        return None


# Helper function to check if a stored procedure exists
def check_procedure_exists(procedure_name):
    try:
        cursor.execute(
            f"""
            SELECT COUNT(*) 
            FROM sys.procedures 
            WHERE name = '{procedure_name}'
        """
        )
        result = cursor.fetchone()
        return result[0] > 0
    except:
        return False


# Function to get complete table definition using sp_GetDDL if available
def get_complete_table_definition(table_name):
    # Check if sp_GetDDL exists (this is a common custom procedure in many environments)
    if check_procedure_exists("sp_GetDDL"):
        try:
            cursor.execute(f"EXEC sp_GetDDL '{table_name}'")
            rows = cursor.fetchall()
            if rows:
                # Combine all rows into a single definition
                return "\n".join([row[0] for row in rows])
        except:
            pass  # Fall back to the alternate method

    # Alternate approach - generate script manually with comprehensive details
    try:
        # First create basic table structure
        cursor.execute(
            f"""
        DECLARE @TableName NVARCHAR(256) = '{table_name}';
        DECLARE @Schema NVARCHAR(128) = PARSENAME(@TableName, 2);
        DECLARE @Table NVARCHAR(128) = PARSENAME(@TableName, 1);
        DECLARE @object_id INT = OBJECT_ID(@TableName);
        
        -- Start with standard header
        DECLARE @Result NVARCHAR(MAX) = 'SET ANSI_NULLS ON' + CHAR(13) + CHAR(10) +
                                       'GO' + CHAR(13) + CHAR(10) +
                                       'SET QUOTED_IDENTIFIER ON' + CHAR(13) + CHAR(10) +
                                       'GO' + CHAR(13) + CHAR(10);
        
        -- Get table properties like compression, filegroup, etc.
        SELECT @Result = @Result + 
            'CREATE TABLE [' + @Schema + '].[' + @Table + '] (' + CHAR(13) + CHAR(10);
            
        -- Add all columns with complete properties
        SELECT @Result = @Result + '    [' + c.name + '] [' + 
            t.name + ']' + 
            CASE 
                WHEN t.name IN ('varchar', 'nvarchar', 'char', 'nchar') 
                    THEN '(' + CASE WHEN c.max_length = -1 THEN 'MAX' ELSE CAST(c.max_length / CASE WHEN t.name LIKE 'n%' THEN 2 ELSE 1 END AS VARCHAR) END + ')' 
                WHEN t.name IN ('decimal', 'numeric') 
                    THEN '(' + CAST(c.precision AS VARCHAR) + ', ' + CAST(c.scale AS VARCHAR) + ')'
                WHEN t.name IN ('datetime2', 'time', 'datetimeoffset')
                    THEN '(' + CAST(c.scale AS VARCHAR) + ')'
                ELSE '' 
            END + 
            -- Identity properties
            CASE WHEN c.is_identity = 1 
                THEN ' IDENTITY(' + CAST(IDENT_SEED(@TableName) AS VARCHAR) + ',' + CAST(IDENT_INCR(@TableName) AS VARCHAR) + ')'
                ELSE '' 
            END +
            -- Computed column definition
            CASE WHEN c.is_computed = 1 
                THEN ' AS ' + cc.definition + CASE WHEN cc.is_persisted = 1 THEN ' PERSISTED' ELSE '' END
                ELSE '' 
            END +
            -- Column properties: nullability, sparse, filestream, etc.
            CASE WHEN c.is_sparse = 1 THEN ' SPARSE' ELSE '' END +
            CASE WHEN c.is_filestream = 1 THEN ' FILESTREAM' ELSE '' END +
            CASE WHEN c.is_computed = 0 THEN 
                CASE WHEN c.is_nullable = 0 THEN ' NOT NULL' ELSE ' NULL' END 
                ELSE '' 
            END +
            -- Default constraints
            CASE WHEN dc.definition IS NOT NULL THEN ' DEFAULT ' + dc.definition ELSE '' END +
            -- Collation if different from database default
            CASE WHEN c.collation_name IS NOT NULL AND c.collation_name <> DATABASEPROPERTYEX(DB_NAME(), 'Collation') 
                THEN ' COLLATE ' + c.collation_name 
                ELSE '' 
            END +
            -- Row GUID column
            CASE WHEN c.is_rowguidcol = 1 THEN ' ROWGUIDCOL' ELSE '' END +
            -- Check constraints belonging to this column (not check table constraints)
            CASE WHEN chk.definition IS NOT NULL AND col_chk.column_id IS NOT NULL 
                THEN ' CHECK ' + chk.definition 
                ELSE '' 
            END +
            ',' + CHAR(13) + CHAR(10)
        FROM sys.columns c
        JOIN sys.types t ON c.user_type_id = t.user_type_id
        LEFT JOIN sys.computed_columns cc ON c.object_id = cc.object_id AND c.column_id = cc.column_id
        LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
        LEFT JOIN sys.check_constraints chk ON chk.parent_object_id = c.object_id AND chk.parent_column_id = c.column_id
        LEFT JOIN sys.columns col_chk ON col_chk.object_id = chk.parent_object_id AND col_chk.column_id = chk.parent_column_id
        WHERE c.object_id = @object_id
        ORDER BY c.column_id;
        
        -- Now add table-level constraints
        
        -- Add table CHECK constraints
        SELECT @Result = @Result + '    CONSTRAINT [' + name + '] CHECK ' + 
            definition + ',' + CHAR(13) + CHAR(10)
        FROM sys.check_constraints 
        WHERE parent_object_id = @object_id 
        AND parent_column_id = 0;  -- Table-level check constraints
        
        -- Add UNIQUE constraints (not implemented as unique indexes)
        SELECT @Result = @Result + '    CONSTRAINT [' + i.name + '] UNIQUE ' +
            CASE WHEN i.type = 1 THEN 'CLUSTERED' ELSE 'NONCLUSTERED' END + ' (' +
            STUFF((SELECT ', [' + c.name + ']' + 
                CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE ' ASC' END
                FROM sys.index_columns ic
                JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                ORDER BY ic.key_ordinal
                FOR XML PATH('')), 1, 2, '') + '),' + CHAR(13) + CHAR(10)
        FROM sys.indexes i
        WHERE i.object_id = @object_id AND i.is_unique_constraint = 1;
        
        -- Add PRIMARY KEY constraint
        SELECT @Result = @Result + '    CONSTRAINT [' + i.name + '] PRIMARY KEY ' +
            CASE WHEN i.type = 1 THEN 'CLUSTERED' ELSE 'NONCLUSTERED' END + ' (' +
            STUFF((SELECT ', [' + c.name + ']' + 
                CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE ' ASC' END
                FROM sys.index_columns ic
                JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
                ORDER BY ic.key_ordinal
                FOR XML PATH('')), 1, 2, '') + ')' + 
            -- Add filegroup info if not on PRIMARY
            CASE WHEN ds.name <> 'PRIMARY' THEN ' ON [' + ds.name + ']' ELSE '' END +
            ',' + CHAR(13) + CHAR(10)
        FROM sys.indexes i
        JOIN sys.data_spaces ds ON i.data_space_id = ds.data_space_id
        WHERE i.object_id = @object_id AND i.is_primary_key = 1;
        
        -- Remove trailing comma if exists and close the table definition
        IF RIGHT(@Result, 3) = ',' + CHAR(13) + CHAR(10)
            SET @Result = LEFT(@Result, LEN(@Result) - 3) + CHAR(13) + CHAR(10);
        
        -- Complete table options
        SELECT @Result = @Result + ')' +
            -- Specify filegroup if table is not on PRIMARY
            CASE WHEN ds.name <> 'PRIMARY' THEN ' ON [' + ds.name + ']' ELSE '' END +
            -- Add any table options like compression
            CASE 
                WHEN p.data_compression = 1 THEN ' WITH (DATA_COMPRESSION = ROW)' 
                WHEN p.data_compression = 2 THEN ' WITH (DATA_COMPRESSION = PAGE)'
                ELSE ''
            END +
            CHAR(13) + CHAR(10) + 'GO' + CHAR(13) + CHAR(10)
        FROM sys.tables t
        JOIN sys.indexes i ON t.object_id = i.object_id
        JOIN sys.data_spaces ds ON i.data_space_id = ds.data_space_id
        JOIN sys.partitions p ON t.object_id = p.object_id AND i.index_id = p.index_id
        WHERE t.object_id = @object_id AND i.index_id <= 1;  -- Clustered index or heap
        
        -- Add all non-clustered indexes that are not implementing constraints
        SELECT @Result = @Result + CHAR(13) + CHAR(10) +
            'CREATE ' + CASE WHEN i.is_unique = 1 THEN 'UNIQUE ' ELSE '' END + 'NONCLUSTERED INDEX [' + 
            i.name + '] ON [' + @Schema + '].[' + @Table + '] (' +
            STUFF((SELECT ', [' + c.name + ']' + 
                CASE WHEN ic.is_descending_key = 1 THEN ' DESC' ELSE ' ASC' END
                FROM sys.index_columns ic
                JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0
                ORDER BY ic.key_ordinal
                FOR XML PATH('')), 1, 2, '') + ')' +
            -- Add included columns if any
            CASE WHEN EXISTS (
                SELECT 1 FROM sys.index_columns ic 
                WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 1
            )
            THEN ' INCLUDE (' + 
                STUFF((SELECT ', [' + c.name + ']'
                    FROM sys.index_columns ic
                    JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                    WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 1
                    ORDER BY ic.key_ordinal
                    FOR XML PATH('')), 1, 2, '') + ')'
            ELSE ''
            END +
            -- Add filegroup if not on PRIMARY
            CASE WHEN ds.name <> 'PRIMARY' THEN ' ON [' + ds.name + ']' ELSE '' END +
            -- Add compression info
            CASE 
                WHEN p.data_compression = 1 THEN ' WITH (DATA_COMPRESSION = ROW)' 
                WHEN p.data_compression = 2 THEN ' WITH (DATA_COMPRESSION = PAGE)'
                ELSE ''
            END +
            CHAR(13) + CHAR(10) + 'GO' + CHAR(13) + CHAR(10)
        FROM sys.indexes i
        JOIN sys.data_spaces ds ON i.data_space_id = ds.data_space_id
        JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
        WHERE i.object_id = @object_id 
        AND i.is_primary_key = 0 
        AND i.is_unique_constraint = 0 
        AND i.type = 2;  -- Only non-clustered indexes
                
        -- Add all foreign key constraints
        SELECT @Result = @Result + CHAR(13) + CHAR(10) +
            'ALTER TABLE [' + @Schema + '].[' + @Table + '] WITH ' + 
            CASE WHEN fk.is_not_trusted = 1 THEN 'NOCHECK' ELSE 'CHECK' END + 
            ' ADD CONSTRAINT [' + fk.name + '] FOREIGN KEY (' +
            STUFF((SELECT ', [' + COL_NAME(fk.parent_object_id, fkc.parent_column_id) + ']'
                FROM sys.foreign_key_columns fkc
                WHERE fkc.constraint_object_id = fk.object_id
                ORDER BY fkc.constraint_column_id
                FOR XML PATH('')), 1, 2, '') + ')' +
            ' REFERENCES [' + OBJECT_SCHEMA_NAME(fk.referenced_object_id) + '].[' + 
            OBJECT_NAME(fk.referenced_object_id) + '] (' +
            STUFF((SELECT ', [' + COL_NAME(fk.referenced_object_id, fkc.referenced_column_id) + ']'
                FROM sys.foreign_key_columns fkc
                WHERE fkc.constraint_object_id = fk.object_id
                ORDER BY fkc.constraint_column_id
                FOR XML PATH('')), 1, 2, '') + ')' +
            -- Add ON UPDATE/DELETE actions
            CASE fk.update_referential_action
                WHEN 1 THEN ' ON UPDATE CASCADE'
                WHEN 2 THEN ' ON UPDATE SET NULL'
                WHEN 3 THEN ' ON UPDATE SET DEFAULT'
                ELSE ''
            END +
            CASE fk.delete_referential_action
                WHEN 1 THEN ' ON DELETE CASCADE'
                WHEN 2 THEN ' ON DELETE SET NULL'
                WHEN 3 THEN ' ON DELETE SET DEFAULT'
                ELSE ''
            END +
            -- Add NOT FOR REPLICATION if needed
            CASE WHEN fk.is_not_for_replication = 1 THEN ' NOT FOR REPLICATION' ELSE '' END +
            CHAR(13) + CHAR(10) + 'GO' + CHAR(13) + CHAR(10)
        FROM sys.foreign_keys fk
        WHERE fk.parent_object_id = @object_id
        ORDER BY fk.name;
        
        -- Add any triggers on the table
        SELECT @Result = @Result + CHAR(13) + CHAR(10) +
            OBJECT_DEFINITION(t.object_id) + CHAR(13) + CHAR(10) + 'GO' + CHAR(13) + CHAR(10)
        FROM sys.triggers t
        WHERE t.parent_id = @object_id AND is_disabled = 0;
        
        SELECT @Result AS definition;
        """
        )

        table_def = cursor.fetchone()
        return table_def.definition if table_def and table_def.definition else None
    except Exception as e:
        print(f"Error generating definition for {table_name}: {str(e)}")
        return None


# Function to collect all database objects and their creation scripts
def collect_object_create_scripts():
    # Get tables
    cursor.execute(
        """
    SELECT 
        SCHEMA_NAME(t.schema_id) + '.' + t.name AS table_name
    FROM sys.tables t
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE s.name NOT LIKE '%tSQLt%'
    AND t.name NOT LIKE '%tSQLt%'
    ORDER BY table_name
    """
    )

    tables = cursor.fetchall()
    for table in tables:
        table_def = get_complete_table_definition(table.table_name)
        if table_def:
            object_create_scripts.append(
                {
                    "name": table.table_name,
                    "type": "TABLE",
                    "definition": table_def,
                }
            )

    # Get views
    cursor.execute(
        """
    SELECT 
        SCHEMA_NAME(v.schema_id) + '.' + v.name AS view_name
    FROM sys.views v
    JOIN sys.schemas s ON v.schema_id = s.schema_id
    WHERE s.name NOT LIKE '%tSQLt%'
    AND v.name NOT LIKE '%tSQLt%'
    ORDER BY view_name
    """
    )

    views = cursor.fetchall()
    for view in views:
        view_def = get_object_definition(view.view_name, "VIEW")
        if view_def:
            object_create_scripts.append(
                {"name": view.view_name, "type": "VIEW", "definition": view_def}
            )

    # Get functions
    cursor.execute(
        """
    SELECT 
        SCHEMA_NAME(f.schema_id) + '.' + f.name AS function_name,
        CASE 
            WHEN f.type = 'FN' THEN 'SCALAR_FUNCTION'
            WHEN f.type = 'IF' THEN 'INLINE_TABLE_VALUED_FUNCTION'
            WHEN f.type = 'TF' THEN 'TABLE_VALUED_FUNCTION'
            ELSE 'FUNCTION'
        END AS function_type
    FROM sys.objects f
    JOIN sys.schemas s ON f.schema_id = s.schema_id
    WHERE f.type IN ('FN', 'IF', 'TF')
    AND s.name NOT LIKE '%tSQLt%'
    AND f.name NOT LIKE '%tSQLt%'
    ORDER BY function_name
    """
    )

    functions = cursor.fetchall()
    for func in functions:
        func_def = get_object_definition(func.function_name, func.function_type)
        if func_def:
            object_create_scripts.append(
                {
                    "name": func.function_name,
                    "type": func.function_type,
                    "definition": func_def,
                }
            )

    # Get stored procedures
    cursor.execute(
        """
    SELECT 
        SCHEMA_NAME(p.schema_id) + '.' + p.name AS proc_name
    FROM sys.procedures p
    JOIN sys.schemas s ON p.schema_id = s.schema_id
    WHERE s.name NOT LIKE '%tSQLt%'
    AND p.name NOT LIKE '%tSQLt%'
    ORDER BY proc_name
    """
    )

    procs = cursor.fetchall()
    for proc in procs:
        proc_def = get_object_definition(proc.proc_name, "PROCEDURE")
        if proc_def:
            object_create_scripts.append(
                {"name": proc.proc_name, "type": "PROCEDURE", "definition": proc_def}
            )

    # Get triggers - fix the schema_id reference
    cursor.execute(
        """
    SELECT 
        SCHEMA_NAME(s.schema_id) + '.' + t.name AS trigger_name
    FROM sys.triggers t
    JOIN sys.objects o ON t.object_id = o.object_id
    JOIN sys.schemas s ON o.schema_id = s.schema_id
    WHERE s.name NOT LIKE '%tSQLt%'
    AND t.name NOT LIKE '%tSQLt%'
    ORDER BY trigger_name
    """
    )

    triggers = cursor.fetchall()
    for trigger in triggers:
        trigger_def = get_object_definition(trigger.trigger_name, "TRIGGER")
        if trigger_def:
            object_create_scripts.append(
                {
                    "name": trigger.trigger_name,
                    "type": "TRIGGER",
                    "definition": trigger_def,
                }
            )


connection_string = os.getenv("CONNECTION_STRING")

connection = pyodbc.connect(connection_string)
cursor = connection.cursor()

# Get all stored procedures
cursor.execute(
    """
SELECT 
    s.name + '.' + p.name AS name
FROM sys.procedures p
JOIN sys.schemas s ON p.schema_id = s.schema_id
WHERE s.name NOT LIKE '%tSQLt%' 
  AND p.name NOT LIKE '%tSQLt%'
ORDER BY s.name, p.name;
"""
)
procedures = cursor.fetchall()


def discover_dependencies(connection_string):

    connection = pyodbc.connect(connection_string)
    cursor = connection.cursor()

    # Get all stored procedures
    cursor.execute(
        """
    SELECT 
        s.name + '.' + p.name AS name
    FROM sys.procedures p
    JOIN sys.schemas s ON p.schema_id = s.schema_id
    WHERE s.name NOT LIKE '%tSQLt%' 
    AND p.name NOT LIKE '%tSQLt%'
    ORDER BY s.name, p.name;
    """
    )
    procedures = cursor.fetchall()

    for procedure in procedures:
        procedure_name = (
            procedure.name.split(".")[1] if "." in procedure.name else procedure.name
        )
        schema_name = procedure.name.split(".")[0] if "." in procedure.name else "dbo"
        full_procedure_name = procedure.name

        # Get all dependencies (tables, views, functions, procedures, triggers)
        cursor.execute(
            f"""
        SELECT 
            ISNULL(OBJECT_SCHEMA_NAME(d.referenced_id), 'dbo') + '.' + OBJECT_NAME(d.referenced_id) AS referenced_name,
            o.type_desc AS object_type
        FROM sys.sql_expression_dependencies d
        JOIN sys.objects o ON d.referenced_id = o.object_id
        WHERE OBJECT_ID('{full_procedure_name}') = d.referencing_id
        AND d.referenced_id IS NOT NULL
        """
        )

        dependencies = cursor.fetchall()
        dependency_list = []

        for dep in dependencies:
            referenced_name = dep.referenced_name
            object_type = dep.object_type

            # Process based on object type
            if object_type == "USER_TABLE":
                # Get column metadata for tables
                cursor.execute(
                    f"""
                SELECT 
                    c.name AS column_name,
                    t.name AS data_type,
                    c.max_length,
                    c.precision,
                    c.scale,
                    c.is_nullable
                FROM sys.columns c
                JOIN sys.types t ON c.user_type_id = t.user_type_id
                WHERE c.object_id = OBJECT_ID('{referenced_name}')
                ORDER BY c.column_id
                """
                )

                columns = cursor.fetchall()
                column_metadata = [
                    {
                        "name": col.column_name,
                        "data_type": col.data_type,
                        "max_length": col.max_length,
                        "precision": col.precision,
                        "scale": col.scale,
                        "is_nullable": col.is_nullable,
                    }
                    for col in columns
                ]

                dependency_list.append(
                    {
                        "name": referenced_name,
                        "type": "TABLE",
                        "columns": column_metadata,
                    }
                )

            elif object_type == "VIEW":
                # Get column metadata for views
                cursor.execute(
                    f"""
                SELECT 
                    c.name AS column_name,
                    t.name AS data_type,
                    c.max_length,
                    c.precision,
                    c.scale,
                    c.is_nullable
                FROM sys.columns c
                JOIN sys.types t ON c.user_type_id = t.user_type_id
                WHERE c.object_id = OBJECT_ID('{referenced_name}')
                ORDER BY c.column_id
                """
                )

                columns = cursor.fetchall()
                column_metadata = [
                    {
                        "name": col.column_name,
                        "data_type": col.data_type,
                        "max_length": col.max_length,
                        "precision": col.precision,
                        "scale": col.scale,
                        "is_nullable": col.is_nullable,
                    }
                    for col in columns
                ]

                dependency_list.append(
                    {
                        "name": referenced_name,
                        "type": "VIEW",
                        "columns": column_metadata,
                    }
                )

            elif object_type in (
                "SQL_STORED_PROCEDURE",
                "SQL_INLINE_TABLE_VALUED_FUNCTION",
                "SQL_SCALAR_FUNCTION",
                "SQL_TABLE_VALUED_FUNCTION",
            ):
                # For procedures and functions, just store the reference
                dependency_type = (
                    "PROCEDURE" if object_type == "SQL_STORED_PROCEDURE" else "FUNCTION"
                )

                # For functions, get the definition
                if dependency_type == "FUNCTION":
                    cursor.execute(
                        f"""
                    SELECT 
                        m.definition
                    FROM sys.sql_modules m
                    WHERE m.object_id = OBJECT_ID('{referenced_name}')
                    """
                    )
                    definition_row = cursor.fetchone()
                    definition = definition_row.definition if definition_row else None

                    dependency_list.append(
                        {
                            "name": referenced_name,
                            "type": dependency_type,
                            "definition": definition,
                        }
                    )
                else:
                    dependency_list.append(
                        {"name": referenced_name, "type": dependency_type}
                    )

            elif object_type == "SQL_TRIGGER":
                dependency_list.append({"name": referenced_name, "type": "TRIGGER"})

            else:
                # For any other object types
                dependency_list.append({"name": referenced_name, "type": object_type})

        procedure_dependencies.append(
            {"name": full_procedure_name, "dependencies": dependency_list}
        )
        print(
            f"Processed procedure: {full_procedure_name} with {len(dependencies)} dependencies"
        )

    # Collect all object create scripts
    collect_object_create_scripts()

    # Save procedures to JSON file
    os.makedirs("output/data", exist_ok=True)
    with open("output/data/procedure_dependencies.json", "w") as f:
        json.dump(procedure_dependencies, f, indent=4)

    # Save object create scripts to JSON file
    with open("output/data/object_create_scripts.json", "w") as f:
        json.dump(object_create_scripts, f, indent=4)

    print("Procedure discovery completed.")
    print(
        f"Created object_create_scripts.json with {len(object_create_scripts)} database objects."
    )

    # Close the database connection
    connection.close()
