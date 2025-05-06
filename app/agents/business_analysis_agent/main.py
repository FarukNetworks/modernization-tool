from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
import uuid
from config.prompt import task
from config.agent import root_agent


session_service = InMemorySessionService()

# Set the agent

inital_state = {
    "stored_procedure_name": "name",
    "stored_procedure_definition": "definition",
    "dependencies": "dependencies",
}

APP_NAME = "Stored Procedure Modernization Analysis"
USER_ID = "project_owner"
SESSION_ID = str(uuid.uuid4())
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
    state=inital_state,
)

print("CREATE NEW SESSION")
print(f"\tSession ID: {SESSION_ID}")

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)

for event in runner.run(
    user_id=USER_ID,
    session_id=SESSION_ID,
    new_message=task,
):
    if event.is_final_response():
        if event.content and event.content.parts:
            print(f"FINAL RESPONSE: {event.content.parts[0].text}")

print("=== SESSION EVENT EXPLORATION ===")
session = session_service.get_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID,
)


# Log final session state
print("=== FINAL SESSION STATE ===")
for key, value in session.state.items():
    print(f"\t{key}: {value}")
