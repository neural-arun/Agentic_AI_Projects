import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# 1. SETUP
BASE_DIR = Path(__file__).resolve().parent
VALUE_FILE_PATH = BASE_DIR / "me" / "my_value.txt"
load_dotenv(override=True)

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

with open(VALUE_FILE_PATH, "r", encoding="utf-8") as f:
    my_value = f.read()

# 2. THE DECISION MODEL
class CapabilityCheck(BaseModel):
    can_do: bool
    reasoning: str
    relevant_skill_from_text: str

# 3. THE ANALYSER FUNCTION
def check_capability(user_question):
    analysis_prompt = f"""
    You are a Technical Gatekeeper for an AI Engineer. 
    Review the user's request and compare it to the ENGINEER'S CAPABILITIES.
    
    ENGINEER'S CAPABILITIES:
    {my_value}
    
    USER REQUEST: "{user_question}"
    
    TASK:
    1. Determine if this task falls under the Engineer's expertise (AI Agents, MCP, CrewAI, Automation, etc.).
    2. If yes, identify the specific line or skill from the text that matches.
    3. If no, explain why it's a mismatch.
    """

    response = client.beta.chat.completions.parse(
        model="google/gemini-2.5-flash-lite", 
        messages=[{"role": "system", "content": analysis_prompt}],
        response_format=CapabilityCheck
    )
    return response.choices[0].message.parsed

# 4. THE RESPONDER FUNCTION
def generate_response(user_question, check):
    if check.can_do:
        reply_prompt = f"""
        The user asked: "{user_question}"
        You have confirmed the engineer CAN do this based on: "{check.relevant_skill_from_text}"
        
        REPLY INSTRUCTIONS:
        - Start with a confident "Yes, I can build that."
        - Briefly (2 sentences) explain the technical approach using tools like {check.relevant_skill_from_text}.
        - Keep it professional and architectural.
        """
    else:
        reply_prompt = f"""
        The user asked: "{user_question}"
        The engineer CANNOT do this. Reasoning: {check.reasoning}
        
        REPLY INSTRUCTIONS:
        - Politely decline the specific task.
        - Pivot to what you DO do (Agentic Workflows, Autonomous Systems, etc.).
        - "I specialize in autonomous agentic systems rather than [user's request]."
        """

    response = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct",
        messages=[{"role": "system", "content": reply_prompt}]
    )
    return response.choices[0].message.content

# 5. THE EXECUTION INTERFACE
def run_bot():
    print("\n--- 🤖 CAPABILITY VERIFIER BOT ---")
    query = input("\nWhat do you want to build? (e.g., 'Can you build a research agent?')\n> ")
    
    print("🔍 Analyzing your value prop...")
    check = check_capability(query)
    
    print("✍️ Generating response...")
    final_reply = generate_response(query, check)
    
    print("\n" + "="*50)
    print(final_reply)
    print("="*50 + "\n")

if __name__ == "__main__":
    run_bot()