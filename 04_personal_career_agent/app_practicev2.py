from dotenv import load_dotenv
import json
from openai import OpenAI
import os
import requests
from pypdf import PdfReader
from pathlib import Path
import gradio as gr

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(override=True)

# Function to send a notification using Telegram Bot API
def push(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram credentials missing in .env")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

# Tool functions
def save_user_details(email, name="name not provided", notes="notes not provided."):
    push(f"<b>New Lead!</b>\n<b>Name:</b> {name}\n<b>Email:</b> {email}\n<b>Notes:</b> {notes}")
    return {"recorded": "ok"}

def save_unknown_qustions(question):
    push(f"<b>Unknown Question:</b>\n{question}")
    return {"recorded" : "ok"}

# JSON Schemas
save_user_details_json = {
    "name": "save_user_details",
    "description": "use this tool to record that a user is interested and provided an email address.",
    "parameters":{
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "email address of this user."},
            "name": {"type": "string", "description": "the user's name if they provided it."},
            "notes": {"type": "string", "description": "Extra context about the conversation."}
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

save_unknown_qustions_json = {
    "name": "save_unknown_qustions",
    "description": "use this tool to record questions that could not be answered",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "the question that could not be answered"},
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [
    {"type": "function", "function": save_user_details_json},
    {"type": "function", "function": save_unknown_qustions_json}
]

class Me:
    def __init__(self):
        self.openai = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.name = "Arun Yadav"
        
        # Load PDF data
        pdf_path = BASE_DIR / "me" / "linkedin.pdf"
        self.linkedin = ""
        if pdf_path.exists():
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                text = page.extract_text()
                if text: self.linkedin += text

        # Load Summary data
        summary_path = BASE_DIR / "me" / "summary.txt"
        self.summary = ""
        if summary_path.exists():
            with open(summary_path, "r", encoding="utf-8") as f:
                self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        tool_results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            
            print(f"Tool called: {tool_name}")
            tool_func = globals().get(tool_name)
            
            content = tool_func(**arguments) if tool_func else {"error": "tool not found"}

            tool_results.append({
                "role": "tool",
                "content": json.dumps(content),
                "tool_call_id": tool_call.id
            })
        return tool_results

    def system_prompt(self):
        return f"""
        You are {self.name}. You are answering questions on your personal website.
        Be professional and engaging. Never break character.
        
        Background: {self.summary}
        LinkedIn: {self.linkedin}
        
        If you don't know something, use 'save_unknown_qustions'.
        If a user is interested, ask for their email and use 'save_user_details'.
        """

    def chat(self, message, history):
        messages = [{"role": "system", "content": self.system_prompt()}]
        
        # FIX: Bullet-proof history parsing
        for turn in history:
            # We explicitly grab only the first two items (user, bot) using indexing
            # to avoid the "too many values to unpack" error if Gradio adds hidden metadata
            if isinstance(turn, (list, tuple)) and len(turn) >= 2:
                # Gradio sometimes wraps text in a tuple if it's a file, so we extract just the string
                user_content = turn[0][0] if isinstance(turn[0], tuple) else turn[0]
                ai_content = turn[1][0] if isinstance(turn[1], tuple) else turn[1]
                
                if user_content: messages.append({"role": "user", "content": user_content})
                if ai_content: messages.append({"role": "assistant", "content": ai_content})
            elif isinstance(turn, dict):
                # Just in case Gradio upgrades you silently to the dictionary format
                messages.append(turn)

        messages.append({"role": "user", "content": message})

        done = False
        while not done:
            response = self.openai.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct", # Switched to a standard, active Groq model
                messages=messages,
                tools=tools
            )
            
            choice = response.choices[0]
            if choice.finish_reason == "tool_calls":
                assistant_msg = choice.message
                
                # FIX: Safely construct a dictionary from the tool call message to append
                # This prevents weird SDK errors when passing objects back into the loop
                safe_assistant_msg = {
                    "role": "assistant",
                    "content": assistant_msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in assistant_msg.tool_calls
                    ]
                }
                messages.append(safe_assistant_msg)
                
                tool_results = self.handle_tool_call(assistant_msg.tool_calls)
                messages.extend(tool_results)
            else:
                done = True
        
        return response.choices[0].message.content

if __name__ == "__main__":
    me = Me()
    gr.ChatInterface(me.chat).launch()