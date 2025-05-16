from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from app.agents.model_configuration import llm


tsqlt_user_guide = """
<tsqlt_user_guide>

Full user guide
This reference contains an explanation of each of the public tables, views, stored procedures and functions provided by tSQLt.

# Test creation and execution

EXEC tSQLt.NewTestClass (tSQLt.NewTestClass '[test_procedure_name]')
EXEC tSQLt.DropClass (tSQLt.DropClass '[test_procedure_name]')
EXEC tSQLt.RunAll (tSQLt.RunAll)
EXEC tSQLt.Run (tSQLt.Run '[test_procedure_name]')
EXEC tSQLt.RenameClass (tSQLt.RenameClass '[test_procedure_name]', '[new_test_procedure_name]')
EXEC tSQLt.ResultSetFilter (tSQLt.ResultSetFilter [int index of result set], '[procedure_name] [parameter_name] = [value (cannot be variable name cannot be +, cast, convert or any other function, and only available values are hardcoded values as the paramataer value)]')
# Assertions

EXEC tSQLt.AssertEmptyTable (tSQLt.AssertEmptyTable '[schema].[table]')
EXEC tSQLt.AssertEquals (tSQLt.AssertEquals '[expected]', '[actual]')
EXEC tSQLt.AssertEqualsString (tSQLt.AssertEqualsString '[expected]', '[actual]')
EXEC tSQLt.AssertEqualsTable (tSQLt.AssertEqualsTable '#expected', '#actual')
EXEC tSQLt.AssertEqualsTableSchema (tSQLt.AssertEqualsTableSchema '[expected]', '[actual]')
EXEC tSQLt.AssertNotEquals (tSQLt.AssertNotEquals '[expected]', '[actual]')
EXEC tSQLt.AssertObjectDoesNotExist (tSQLt.AssertObjectDoesNotExist '[schema].[object]')
EXEC tSQLt.AssertObjectExists (tSQLt.AssertObjectExists '[schema].[object]')
EXEC tSQLt.AssertResultSetsHaveSameMetaData (tSQLt.AssertResultSetsHaveSameMetaData '[expected]', '[actual]')
EXEC tSQLt.Fail (tSQLt.Fail 'string', @ErrorMessage) (DO NOT USE + @ErrorMessage USE , @ErrorMessage)
EXEC tSQLt.AssertLike (tSQLt.AssertLike '[pattern]', '[actual]')
EXEC tSQLt.Expectations (tSQLt.Expectations)

EXEC tSQLt.ExpectException (tSQLt.ExpectException '[expected_exception]')
EXEC tSQLt.ExpectNoException (tSQLt.ExpectNoException)

# Isolating dependencies

EXEC tSQLt.ApplyConstraint (tSQLt.ApplyConstraint '[schema].[table]', '[constraint]')
EXEC tSQLt.FakeFunction (tSQLt.FakeFunction '[schema].[function]', '[fake_function_name_that_returns_expected_value]')
EXEC tSQLt.FakeTable (tSQLt.FakeTable '[schema].[table]', @Identity = 'preserve identity default 0 can be 1', @ComputedColumns = 'preserve computed columns default 0 can be 1', @Defaults = 'preserve default constraints default 0 can be 1')
EXEC tSQLt.RemoveObjectIfExists (tSQLt.RemoveObjectIfExists '[schema].[object]')
EXEC tSQLt.SpyProcedure (tSQLt.SpyProcedure '[schema].[procedure]')
EXEC tSQLt.ApplyTrigger (tSQLt.ApplyTrigger '[schema].[trigger]')
EXEC tSQLt.RemoveObject (tSQLt.RemoveObject '[schema].[object]')
EXEC tSQLt.PrepareTableForFaking (tSQLt.PrepareTableForFaking '[schema_name]', '[table_name_without_schema]') [USE THIS TO PREPARE THE TABLE FOR FAKING FOR TABLES THAT HAVE COLUMNS WITH AUTOPOPULATED VALUES OR CALCULATIONS. THIS SHOULD BE USED BEFORE USING tSQLt.FakeTable]

</tsqlt_user_guide>
"""


# Set the agent
root_agent = Agent(
    name="sql_test_generation_agent",
    model=LiteLlm(model=llm),
    description="Generate SQL test code for the tSQLt framework",
    instruction=f"""
You are a highly experienced tSQLt test developer. 
You write tests that are stable, execution-safe, and follow strict standards.

<environment>
tSQLt version: 1.0.8083.3529
SQL Server version: 15.00
MSSQL Server: SQL Server 2019
</environment>

<responsibilities>
- Write tests based on procedure logic
- Use correct temp table patterns
- Avoid known SQL errors (type mismatch, column count issues)
</responsibilities>

<important_rules>
<rule>Do not use NVARCHAR(MAX) in AssertEquals — use NVARCHAR(n)</rule>
<rule>Fake all tables referenced by the procedure</rule>
<rule>Use temp tables (#expected) in AssertEqualsTable, not table variables</rule>
<rule>Generate only SQL code without any markdown, explanations or comments outside the SQL code</rule>
<rule>Format your output as raw SQL that can be directly executed</rule>
<rule>DO NOT include the EXEC tSQLt.NewTestClass statement in your output. This will be added automatically at the file level.</rule>
</important_rules>

<allowed_tsqlt_functions>
{tsqlt_user_guide}
</allowed_tsqlt_functions>

<format>
Your response must contain only the SQL code for the test procedure.
DO NOT include code block markers like ```sql or ```.
DO NOT add extra explanations before or after the code.
DO NOT include EXEC tSQLt.NewTestClass statements in your output.
Return only the raw SQL code for the test procedure.
</format>
""",
)
