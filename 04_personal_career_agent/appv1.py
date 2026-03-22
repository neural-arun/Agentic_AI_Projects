# Load environment variables from a .env file (API keys, tokens, etc.)
from dotenv import load_dotenv

# Import OpenAI client to talk to GPT models
from openai import OpenAI

# Built-in modules
import json        # for handling JSON (convert string <-> dict)
import os          # for accessing environment variables
import requests    # for making HTTP requests (API calls)

# Library to read PDF files
from pypdf import PdfReader

# Library to create a web UI (chat interface)
import gradio as gr


# Load environment variables into Python (like OPENAI_API_KEY, PUSHOVER_TOKEN)
load_dotenv(override=True)


# Function to send a push notification using Pushover API
def push(text):
    requests.post(  # send POST request to API
        "https://api.pushover.net/1/messages.json",
        data={      # data sent in request body
            "token": os.getenv("PUSHOVER_TOKEN"),  # app token from .env
            "user": os.getenv("PUSHOVER_USER"),    # user key from .env
            "message": text,                       # message content
        }
    )


# Tool function: save user email + info
def record_user_details(email, name="Name not provided", notes="not provided"):
    # Send notification with user details
    push(f"Recording {name} with email {email} and notes {notes}")
    
    # Return response (this goes back to the AI)
    return {"recorded": "ok"}


# Tool function: save unknown questions
def record_unknown_question(question):
    # Send notification with the question
    push(f"Recording {question}")
    
    # Return response
    return {"recorded": "ok"}


# JSON schema describing tool 1 (VERY IMPORTANT for AI)
record_user_details_json = {
    "name": "record_user_details",  # must match function name
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    
    # Defines what inputs the function takes
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Extra context about the conversation"
            }
        },
        "required": ["email"],  # email is mandatory
        "additionalProperties": False
    }
}


# JSON schema for second tool
record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered",
    
    "parameters": {
        "type": "object",
        "properties ": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}


# List of tools passed to the AI
tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json}
]


# Main AI agent class
class Me:

    # Constructor (runs when object is created)
    def __init__(self):
        self.openai = OpenAI()  # create OpenAI client
        self.name = "Ed Donner" # persona name

        # Read LinkedIn PDF
        reader = PdfReader("me/linkedin.pdf")
        
        self.linkedin = ""  # empty string to store text
        
        # Loop through all pages of PDF
        for page in reader.pages:
            text = page.extract_text()  # extract text from page
            
            # Only add if text exists
            if text:
                self.linkedin += text  # append text

        # Read summary text file
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()  # store full text


    # Handles tool execution when AI requests it
    def handle_tool_call(self, tool_calls):
        results = []  # list to store results

        # Loop through each tool call
        for tool_call in tool_calls:
            tool_name = tool_call.function.name  # get function name
            
            # Convert JSON string → Python dict
            arguments = json.loads(tool_call.function.arguments)
            
            print(f"Tool called: {tool_name}", flush=True)

            # Find function by name from global scope
            tool = globals().get(tool_name)

            # Call function with arguments if it exists
            result = tool(**arguments) if tool else {}

            # Add result in format expected by OpenAI
            results.append({
                "role": "tool",
                "content": json.dumps(result),  # convert dict → JSON string
                "tool_call_id": tool_call.id
            })

        return results  # return all tool results


    # Creates system prompt (AI personality + instructions)
    def system_prompt(self):
        system_prompt =     f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging. \
If you don't know the answer, use record_unknown_question tool. \
If the user shows interest, ask for email and use record_user_details tool."

        # Add summary + LinkedIn context
        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"

        # Final instruction
        system_prompt += f"Stay in character as {self.name}."

        return system_prompt


    # Main chat function (this is the brain loop)
    def chat(self, message, history):

        # Build conversation messages
        messages = [
            {"role": "system", "content": self.system_prompt()}
        ] + history + [
            {"role": "user", "content": message}
        ]

        done = False  # loop control

        # Loop until no tool call is needed
        while not done:

            # Call OpenAI API
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools
            )

            # Check if AI wants to use a tool
            if response.choices[0].finish_reason == "tool_calls":

                message = response.choices[0].message
                tool_calls = message.tool_calls  # get tool requests

                # Execute tools
                results = self.handle_tool_call(tool_calls)

                # Add AI message + tool results back into conversation
                messages.append(message)
                messages.extend(results)

            else:
                # No tool needed → exit loop
                done = True

        # Return final AI response
        return response.choices[0].message.content


# Run the app
if __name__ == "__main__":

    me = Me()  # create AI agent

    # Launch chat UI in browser
    gr.ChatInterface(me.chat, type="messages").launch()