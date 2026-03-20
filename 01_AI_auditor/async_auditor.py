import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 1. Foundation
load_dotenv(override=True)

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

groq_client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

# LIMITER: Only allow 2 ads to process at the exact same time to avoid 429 errors
sem = asyncio.Semaphore(2)

# 2. Input Data
ads_to_audit = [
    "Get rich quick with our AI-powered crypto bot! 100% guaranteed returns. Don't be a boomer, join the moon mission now!",
    "Our AI tool helps you automate data entry. No magic, just smart algorithms. Try it for 14 days; if it doesn't save you 5 hours a week, we'll give you a full refund.",
    "Tired of dieting? Our magic blue juice melts 10 pounds of fat in 7 days while you sleep. No exercise needed.",
    "Over 10,000 marathon runners trust our hydration salts. Science-backed electrolytes with zero added sugar. Feel the difference on your next run."
]

# 3. Specialist Logic
async def get_specialist_feedback(spec, ad):
    t_client = groq_client if spec["provider"] == "groq" else client
    print(f"    [AGENT] {spec['name']} working...")
    
    try:
        res = await t_client.chat.completions.create(
            model=spec["model"],
            messages=[
                {"role": "system", "content": spec["role"]},
                {"role": "user", "content": f"Review this ad: {ad}"}
            ]
        )
        return f"#### {spec['name']} Analysis:\n{res.choices[0].message.content}"
    except Exception as e:
        return f"#### {spec['name']} Analysis:\nError: {str(e)}"

# 4. Single Ad Workflow (Protected by Semaphore)
async def audit_single_ad(ad):
    async with sem: # The bouncer lets the ad in
        print(f"\n🚀 Starting Audit: {ad[:30]}...")
        
        specialists = [
            {"name": "The Cynic", "model": "llama-3.3-70b-versatile", "provider": "groq", "role": "Analyze for scams/fake claims."},
            {"name": "The Lawyer", "model": "google/gemini-2.5-flash-lite", "provider": "openrouter", "role": "Identify FTC violations."},
            {"name": "The Gen-Z Expert", "model": "llama-3.3-70b-versatile", "provider": "groq", "role": "Review tone/authenticity."}
        ]

        # Get Specialist Feedback
        feedback_tasks = [get_specialist_feedback(s, ad) for s in specialists]
        feedbacks = await asyncio.gather(*feedback_tasks)
        together = "\n\n".join(feedbacks)

        # Fixer and Judge
        fixer_task = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Expert Copywriter. Fix the ad."}, {"role": "user", "content": f"Ad: {ad}\n\nFeedback: {together}"}]
        )
        
        judge_task = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Risk Auditor. Scale 1-10."}, {"role": "user", "content": f"Review ad: {ad}\n\nFeedback: {together}"}]
        )

        fixer_res, judge_res = await asyncio.gather(fixer_task, judge_task)
        
        return {
            "ad": ad,
            "report": judge_res.choices[0].message.content,
            "rewrite": fixer_res.choices[0].message.content
        }

# 5. Main Execution
async def main():
    print(f"Running Parallel Audit (Max 2 at once to prevent Rate Limits)...")
    
    audit_tasks = [audit_single_ad(ad) for ad in ads_to_audit]
    results = await asyncio.gather(*audit_tasks)

    output = "# CALIBRATED BRAND AUDIT REPORT\n\n"
    for r in results:
        output += f"## 📢 TARGET AD\n> {r['ad']}\n\n"
        output += f"### ⚖️ RISK ANALYSIS\n{r['report']}\n\n"
        output += f"### ✍️ SUGGESTED REWRITE\n{r['rewrite']}\n\n"
        output += "---\n\n"

    with open("brand_audit_report.md", "w", encoding="utf-8") as f:
        f.write(output)
    
    print("\n" + "="*40)
    print("SUCCESS: All ads processed.")
    print("Report saved: brand_audit_report.md")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())