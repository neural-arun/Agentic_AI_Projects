import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. Foundation & Bridges
load_dotenv(override=True)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

# 2. Input Data
ads_to_audit = [
    "Get rich quick with our AI-powered crypto bot! 100% guaranteed returns. Don't be a boomer, join the moon mission now!",
    "Our AI tool helps you automate data entry. No magic, just smart algorithms. Try it for 14 days; if it doesn't save you 5 hours a week, we'll give you a full refund.",
    "Tired of dieting? Our magic blue juice melts 10 pounds of fat in 7 days while you sleep. No exercise needed.",
    "Over 10,000 marathon runners trust our hydration salts. Science-backed electrolytes with zero added sugar. Feel the difference on your next run."
]

# 3. Specialist Personas
specialists = [
    {
        "name": "The Cynic",
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "role": "Skeptical customer. Flag 'too good to be true' scams. Acknowledge trust signals like trials."
    },
    {
        "name": "The Lawyer",
        "model": "google/gemini-2.5-flash-lite",
        "provider": "openrouter",
        "role": "Legal auditor. Flag FTC violations. Distinguish between standard marketing and illegal claims."
    },
    {
        "name": "The Gen-Z Expert",
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "role": "Trend expert. Flag aggressive, scammy slang or 'cringe' marketing."
    }
]

def run_audit(target_ad):
    all_feedback = []
    print(f"\n--- Processing: {target_ad[:40]}... ---")

    # Step A: Specialists
    for spec in specialists:
        print(f"  > Consulting {spec['name']}...")
        t_client = groq_client if spec["provider"] == "groq" else client
        res = t_client.chat.completions.create(
            model=spec["model"],
            messages=[{"role": "system", "content": spec["role"]}, {"role": "user", "content": target_ad}]
        )
        all_feedback.append(f"### {spec['name']} Feedback:\n{res.choices[0].message.content}")

    together = "\n\n".join(all_feedback)

    # Step B: The Fixer
    print("  > Professional Copywriter is rewriting...")
    fixer_res = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an Expert Copywriter. If the ad is bad, fix it. If it is good, sharpen it."},
            {"role": "user", "content": f"Ad: {target_ad}\n\nFeedback: {together}"}
        ]
    )
    rewritten = fixer_res.choices[0].message.content

    # Step C: The Judge
    print("  > The Judge is finalizing the report...")
    judge_prompt = f"""
    You are an Objective Risk Auditor. 
    Review the ad: "{target_ad}"
    Feedback provided: {together}
    
    Instructions:
    - 1-3: Safe
    - 4-6: Caution
    - 7-10: Danger/Scam
    
    Provide: 
    1. Top Risks
    2. Risk Score (out of 10)
    3. Final Verdict (Go / No-Go / Caution)
    """
    
    judge_res = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": judge_prompt}]
    )
    
    return {
        "ad": target_ad,
        "report": judge_res.choices[0].message.content,
        "rewrite": rewritten
    }

# 4. Main Execution
results = []
for ad in ads_to_audit:
    results.append(run_audit(ad))

# 5. Build Markdown File
markdown_content = "# PROFESSIONAL BRAND AUDIT REPORT\n\n"

# Add a simple Markdown Table at the top
markdown_content += "## Executive Summary Dashboard\n\n"
markdown_content += "| Ad Preview | Status |\n"
markdown_content += "| :--- | :--- |\n"

for r in results:
    verdict = "CHECK"
    if "No-Go" in r['report']: verdict = "❌ REJECT"
    elif "Go" in r['report'] or "Safe" in r['report']: verdict = "✅ PASS"
    else: verdict = "⚠️ CAUTION"
    
    markdown_content += f"| {r['ad'][:50]}... | {verdict} |\n"

markdown_content += "\n---\n\n"

# Detailed Sections
for r in results:
    markdown_content += f"## ORIGINAL AD\n> {r['ad']}\n\n"
    markdown_content += f"### ANALYSIS\n{r['report']}\n\n"
    markdown_content += f"### SUGGESTED REWRITE\n{r['rewrite']}\n\n"
    markdown_content += "---\n\n"

# Save
with open("brand_audit_report.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)

print("\n" + "="*40)
print("SUCCESS: 'brand_audit_report.md' generated.")
print("="*40)