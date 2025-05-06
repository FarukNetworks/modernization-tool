from google.genai import types

task = types.Content(
    role="user",
    parts=[
        types.Part(
            text="""
THIS IS THE TASK
"""
        )
    ],
)
