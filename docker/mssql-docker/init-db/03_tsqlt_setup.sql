SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE PROCEDURE [tSQLt].[PrepareTableForFaking]
      @SchemaName NVARCHAR(MAX),
      @TableName NVARCHAR(MAX)
AS

-- This is not part of the standard tSQLt library
-- See https://harouny.com/2013/04/19/tsqlt-taketable-indexed-view/ (original source)
-- and https://github.com/tSQLt-org/tSQLt/issues/17
--     https://gist.github.com/papsl/30d5f0df925465e41b2e
--     http://tech.4pi.si/2015/01/tsqlt-faketable-fails-with-error-cannot.html

-- 2018-09-18 DFB - Fixed to work on objects that are not in the dbo schema
-- 2019-05-27 DFB - Replace only the first occurrence of CREATE in the object definition, with ALTER
--                - Remove only the first occurrence of WITH SCHEMABINDING in the object definition

BEGIN
 
  --remove brackets
  SELECT @TableName = PARSENAME(@TableName,1) 
  SELECT @SchemaName = PARSENAME(@SchemaName,1) 
 
-- delete temptable
  IF EXISTS(SELECT * FROM tempdb..sysobjects WHERE id = OBJECT_ID('tempdb.dbo.#temp'))
    DROP TABLE #TEMP
 
  --recursively get all referencing dependencies
;WITH ReferencedDependencies (parentId, name, LEVEL)
  AS(
      SELECT DISTINCT o.object_id AS parentId, o.name, 0 AS LEVEL
        FROM sys.sql_expression_dependencies AS d
        JOIN sys.objects AS o
          ON d.referencing_id = o.object_id
            AND o.type IN ('FN','IF','TF', 'V', 'P')
            AND is_schema_bound_reference = 1
        WHERE
          d.referencing_class = 1 AND referenced_entity_name = @TableName AND referenced_schema_name = @SchemaName
      UNION ALL
      SELECT o.object_id AS parentId, o.name, LEVEL +1
        FROM sys.sql_expression_dependencies AS d
        JOIN sys.objects AS o
                ON d.referencing_id = o.object_id
            AND o.type IN ('FN','IF','TF', 'V', 'P')
            AND is_schema_bound_reference = 1
        JOIN ReferencedDependencies AS RD
                ON d.referenced_id = rd.parentId
  )
 
  -- select all objects referencing this table in reverse level order
  SELECT DISTINCT IDENTITY(INT, 1,1) AS id, name, OBJECT_DEFINITION(parentId) as obj_def, parentId as obj_Id , LEVEL
  INTO #TEMP
  FROM ReferencedDependencies
  WHERE OBJECT_DEFINITION(parentId) LIKE '%SCHEMABINDING%'
  ORDER BY LEVEL DESC
  OPTION (Maxrecursion 1000);
 
  --prepere the query to remove all dependent indexes (this is nessesary to removing (with schemabinding) later)
  DECLARE @qryRemoveIndexes NVARCHAR(MAX);
  SELECT @qryRemoveIndexes = (
  SELECT 'DROP INDEX ' + i.name + ' ON ' + OBJECT_SCHEMA_NAME(o.id) + '.' + OBJECT_NAME(o.id) + ';' + CHAR(10) -- XML only uses LF (Unix style), not CR
  FROM sys.sysobjects AS o
  INNER JOIN #TEMP ON o.id = #TEMP.obj_Id
  INNER JOIN sys.sysindexes AS i ON i.id = o.id
  where i.indid = 1 -- 1 = Clustered index (we are only interested in clusterd indexes)
  FOR XML PATH(''));
  --excute @qryRemoveIndexes
  exec sp_executesql @qryRemoveIndexes;
 
  --change the definition for removing (with schemabinding) from those objects
  DECLARE @currentRecord INT
  DECLARE @qryRemoveWithSchemabinding NVARCHAR(MAX)
  SET @currentRecord = 1
  WHILE (@currentRecord <= (SELECT COUNT(1) FROM #TEMP) )
  BEGIN
          SET @qryRemoveWithSchemabinding = ''
          SELECT @qryRemoveWithSchemabinding = #TEMP.obj_def
            FROM #TEMP
            WHERE #TEMP.id = @currentRecord

          -- Replace only the first occurrence of CREATE in the object definition, with ALTER
          IF CHARINDEX ('CREATE', @qryRemoveWithSchemabinding COLLATE Latin1_General_CI_AI) > 0    -- case insensitive search
            SET @qryRemoveWithSchemabinding = STUFF (@qryRemoveWithSchemabinding, 
                                                     CHARINDEX ('CREATE', @qryRemoveWithSchemabinding COLLATE Latin1_General_CI_AI), 
                                                     LEN ('CREATE'), 'ALTER');

          -- Remove only the first occurrence of WITH SCHEMABINDING in the object definition
          IF CHARINDEX ('WITH SCHEMABINDING', @qryRemoveWithSchemabinding COLLATE Latin1_General_CI_AI) > 0    -- case insensitive search
            SET @qryRemoveWithSchemabinding = STUFF (@qryRemoveWithSchemabinding, 
                                                     CHARINDEX ('WITH SCHEMABINDING', @qryRemoveWithSchemabinding COLLATE Latin1_General_CI_AI), 
                                                     LEN ('WITH SCHEMABINDING'), NULL);

          --excute @qryRemoveWithSchemabinding
          EXEC sp_executeSQL @qryRemoveWithSchemabinding;
          SET @currentRecord = @currentRecord + 1
  END
 
END
GO
