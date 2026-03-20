import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# 1. SMART PATHING
BASE_DIR = Path(__file__).resolve().parent
VALUE_FILE_PATH = BASE_DIR / "me" / "my_value.txt"
SAVE_PATH = BASE_DIR / "outreach_draft.md"

# 2. LOAD ENV
load_dotenv(override=True)

# 3. INITIALIZE PROVIDERS
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

# 4. READ YOUR VALUE FILE
try:
    with open(VALUE_FILE_PATH, "r", encoding="utf-8") as f:
        my_value = f.read()
    print(f"✅ Success! Loaded your Superpowers from: {VALUE_FILE_PATH}")
except FileNotFoundError:
    print(f"❌ Error: Could not find 'my_value.txt' in the 'me' folder.")
    exit()

# 5. DATA MODELS FOR EVALUATION
class Evaluation(BaseModel):
    is_acceptable: bool
    feedback: str

# 6. THE ACTOR: Focuses on Problem-Solving & Value
def generate_value_pitch():
    actor_system_prompt = f"""
    You are a high-level Agentic AI Engineer. Write a cold email that sells your ABILITY TO SOLVE PROBLEMS.
    
    YOUR CAPABILITIES: 
    {my_value}
    
    RULES:
    - ABSOLUTE LIMIT: 200 words.
    - Start with a punchy observation about manual business waste.
    - Mention ONE specific high-value build (e.g., Multi-agent research teams or MCP-powered tool ecosystems).
    - Focus on the RESULT (saving time, reducing headcount, or 24/7 autonomous ops).
    - NO "I am writing to...".
    - NO "I hope you are well".
    - End with a low-friction "soft ask" (e.g., "Worth a look?" or "Can I send over a 2-minute demo?").
    - Respond ONLY with the email text.
    """
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": actor_system_prompt}]
    )
    return response.choices[0].message.content

# 7. THE EVALUATOR: The "Cringe & Fluff" Filter
def evaluate_pitch(draft):
    evaluator_prompt = f"""
    You are a busy, skeptical Founder who deletes 99% of cold emails.
    Critique this "Value-First" email draft:
    
    DRAFT: {draft}

    REJECT IF:
    - It sounds like a desperate job seeker.
    - It uses "Unlock", "Revolutionize", or "Game-changer".
    - It is over 200 words.
    - It doesn't mention a specific technical framework (CrewAI, LangGraph, MCP, etc.).
    - It fails to sound like a specialized engineer who builds real systems.
    """
    
    response = openrouter_client.beta.chat.completions.parse(
        model="google/gemini-2.5-flash-lite", 
        messages=[{"role": "system", "content": evaluator_prompt}],
        response_format=Evaluation
    )
    return response.choices[0].message.parsed

# 8. EXECUTION
def run_value_sniper():
    print("\n" + "="*50)
    print("🎯 AGENTIC VALUE-PITCH GENERATOR")
    print("="*50)
    
    print("\n--- 🎯 Drafting based on your Value Prop... ---")
    draft = generate_value_pitch()
    
    print("--- ⚖️ Evaluating for 'Cringe' and 'Impact'... ---")
    evaluation = evaluate_pitch(draft)
    
    final_email = ""

    if evaluation.is_acceptable:
        print("✅ PASS: High-impact email created.")
        final_email = draft
    else:
        print(f"❌ REJECTED: {evaluation.feedback}")
        print("--- 🔄 Refining the pitch... ---")
        
        retry_prompt = f"""
        REWRITE THIS EMAIL. IT WAS REJECTED BY A SKEPTICAL FOUNDER FOR: {evaluation.feedback}
        - 80 words max.
        - Focus on being a 'Builder of Systems'.
        - Keep the mention of CrewAI, LangGraph, or MCP.
        - Respond ONLY with the email. NO PREAMBLE.
        ORIGINAL: {draft}
        """
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": retry_prompt}]
        )
        final_email = response.choices[0].message.content

    # Clean and Save
    final_email = final_email.replace("```markdown", "").replace("```", "").strip()
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        f.write(final_email)
    
    print(f"\n✅ DONE! Value-Pitch saved to: {SAVE_PATH}")
    print("\nFINAL PITCH:\n" + "-"*30 + f"\n{final_email}\n" + "-"*30)

if __name__ == "__main__":
    run_value_sniper()