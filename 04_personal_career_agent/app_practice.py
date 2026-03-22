from dotenv import load_dotenv # to load the env secrets.
import json   # for handling json (convert string to json or json to string)
from openai import OpenAI # used to talk to GPT models.
import os  # for accessing the enviornment variables.
import requests # for sending the request to models using api providers. basically making the http request (api calls)
from pypdf import PdfReader   # used to read pdf text from pdf files.
from pathlib import Path
import gradio as gr # library to create a web UI.
BASE_DIR = Path(__file__).resolve().parent

print(BASE_DIR)
load_dotenv(override=True)  #load the environment variables into Python.

# function to send a push notification using pushover api.
def push(text):
    requests.post(# SENDS POST REQUEST TO API.
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text
        }
    )

#Tool fuction: save user email + info.
def save_user_details(email,name="name not provided",notes="notes not provided."):
    # send notification with user details.
    push(f"Recording {name} with email {email} and notes {notes}")
    # return response: this goes back to AI.
    return {"recorded": "ok"}

def save_unknown_qustions(question):
    push(f"recording {question}")
    return {"recorded" : "ok"}

# JSON Schema for tool 1 (very important for AI)

save_user_details_json = {
    "name": "save_user_details",
    "description": "use this tool to record that a user is interested and like being in touch and provided an email address.",
    "parameters":{
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "email address of this user."
            },
            "name": {
                "type": "string",
                "description": "the user's name if they provided it."
            },
            "notes": {
                "type": "string",
                "description": "Extra context about the conversation if any."
            }
        },
        "required": ["email"], # email is mandatory.
        "additionalproperties": False
    }
}


# json schema for the unknown questions.
save_unknown_qustions_json = {
    "name": "save_unknown_qustions",
    "description": "always use this tool to record questions that could not be answered",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "the question that could not be answered"
            },

        },
        "required": ["question"],
        "additionalproperties": False
    }
}


# list of tools passed to AI. 
tools = [
    {"type": "function", "function": save_user_details_json},
    {"type": "function", "function": save_unknown_qustions_json}
]

#main AI agent class
class Me:
    def __init__(self):
        self.openai = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.name = "Arun Yadav"
        reader = PdfReader(BASE_DIR/"me/linkedin.pdf")
        self.linkedin = ""    # empty string to store the linkedin text.

        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text

        with open(BASE_DIR/"me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read() ## store full text.

# Handles tool execution when AI requests it.
    def handle_tool_call(self, tool_calls):
        results = []

        for tool_call in tool_calls:
            tool_name = tool_call.function.name         # it get the function name
            #convert the json string to python dict.
            arguments = json.loads(tool_call.function.arguments)

            print(f"Tool called: {tool_name}", flush=True)

            tool = globals().get(tool_name) #finds function by name from global scope.

            # call function with arguments if it need to.
            results = tool(**arguments) if tool else {}

            # Add result in format expected by OpenAI
            results.append({
                "role": "tool",
                "content": json.dumps(results),
                "tool_call_id": tool_call.id
            })

        return results      # return all tool results.
    
    # Creates system prompt (AI personality + instructions)
    def system_prompt(self):
        system_prompt = f"""
                        You are acting as {self.name}. you are answering questions on {self.name}'s website
                        particularly questions related to {self.name}'s career background, skills and experience.
                        your responsibility is to represent {self.name} for interaction on the {self.name}'s website
                        as faithfully as possible.
                        You are given a summary of {self.name}'s background and linkedin profile which you can use
                        to answer questions.
                        Be professional and engaging and fun.
                        If you do not know the answer of the question use tool 'save_unknown_question' tool.
                        if user shows interest ask for email and use save_user_details tools"""
        
        system_prompt += f"\n\n## summary:\n {self.summary}"
        system_prompt += f"linkedin Profile: {self.linkedin}"
        system_prompt += f"Always stay in character as {self.name}, never break this character at any cost."

        return system_prompt
    


    # Main chat function (this is the brain loop)
    def chat(self, message, history):
        messages = [
            {"role": "system", "content": self.system_prompt()}
        ] + history + [
            {"role": "user", "content": message}
        ]

        done  = False
        while not done:
            response = self.openai.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=messages,
                tools=tools
            )
            if response.choices[0].finish_reason == "tool_calls":
                message = response.choices[0].message
                tool_calls = message.tool_calls

                results = self.handle_tool_call(tool_calls)
                messages.append(message)
                messages.extend(results)

            else:
                done = True
        return response.choices[0].message.content
    
if __name__ == "__main__":

    me = Me()  # create AI agent

    # Launch chat UI in browser
    gr.ChatInterface(me.chat, type="messages").launch()