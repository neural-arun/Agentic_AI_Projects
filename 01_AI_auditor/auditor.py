import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from fpdf import FPDF

# PDF Class Definition
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Brand Risk Audit Report', 0, 1, 'C')
        self.ln(10)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# 1. Foundation & Bridges
load_dotenv(override=True)

pdf = PDFReport()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

# 2. The Input (Mix of Scams and Quality Ads)
ads_to_audit = [
    "Get rich quick with our AI-powered crypto bot! 100% guaranteed returns. Don't be a boomer, join the moon mission now!",
    "Our AI tool helps you automate data entry. No magic, just smart algorithms. Try it for 14 days; if it doesn't save you 5 hours a week, we'll give you a full refund.",
    "Tired of dieting? Our magic blue juice melts 10 pounds of fat in 7 days while you sleep. No exercise needed.",
    "Over 10,000 marathon runners trust our hydration salts. Science-backed electrolytes with zero added sugar. Feel the difference on your next run."
]

# 3. Re-Calibrated Specialists
specialists = [
    {
        "name": "The Cynic",
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "role": "Analyze for 'Too Good To Be True' claims. Flag '100% guarantees' on investments or 'magic' results. If a claim is backed by a trial or refund policy, acknowledge that as a trust signal."
    },
    {
        "name": "The Lawyer",
        "model": "google/gemini-2.5-flash-lite",
        "provider": "openrouter",
        "role": "Identify FTC violations. High risk: Unsubstantiated health/wealth claims. Low risk: Standard marketing puffery, refund policies, and trial periods. Do not flag standard business offers as illegal."
    },
    {
        "name": "The Gen-Z Expert",
        "model": "llama-3.3-70b-versatile",
        "provider": "groq",
        "role": "Review tone and authenticity. Flag aggressive slang used by 'scammers'. If an ad is professional and straightforward (like the data entry tool), mark it as 'Safe/Authentic'."
    }
]

def run_audit(target_ad):
    all_feedback = []
    print(f"\n--- Auditing: {target_ad[:50]}... ---")

    for specialist in specialists:
        print(f"  > Consulting {specialist['name']}...")
        target_client = groq_client if specialist["provider"] == "groq" else client
        
        response = target_client.chat.completions.create(
            model=specialist["model"],
            messages=[
                {"role": "system", "content": specialist["role"]},
                {"role": "user", "content": f"Review this ad: {target_ad}"}
            ]
        )
        feedback = response.choices[0].message.content
        all_feedback.append(f"### {specialist['name']} Feedback:\n{feedback}")

    together = "\n\n".join(all_feedback)

    # Step B: The Fixer
    print("  > Professional Copywriter is rewriting...")
    fixer_response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are an Expert Copywriter. If the ad is already good, make it even sharper. If it is a scam, transform it into a legitimate, compliant business offer."},
            {"role": "user", "content": f"Original Ad: {target_ad}\n\nFeedback:\n{together}"}
        ]
    )
    rewritten_ad = fixer_response.choices[0].message.content

    # Step C: The Judge (The Objective Calibrator)
    print("  > The Judge is finalizing the report...")
    judge_prompt = f"""
    You are an Objective Risk Auditor. Use this scale:
    1-3 (Safe): Standard marketing, clear terms, no wild claims.
    4-6 (Caution): Aggressive claims but possible with proof.
    7-10 (High Risk): Blatant scams, illegal guarantees, 'magic' health claims.

    Review the ad: "{target_ad}"
    Feedback: {together}
    
    Provide:
    1. Top Risks (Be concise. If safe, say 'Minimal')
    2. Risk Score (1-10)
    3. Final Verdict (Go / No-Go / Caution)
    """
    
    judge_response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": judge_prompt}]
    )
    
    report_text = judge_response.choices[0].message.content
    return f"## ANALYSIS\n{report_text}\n\n## SUGGESTED REWRITE\n{rewritten_ad}"

# 4. Main Execution
final_markdown = "# CALIBRATED BRAND RISK REPORT\n\n"

for ad in ads_to_audit:
    report_section = run_audit(ad)
    final_markdown += f"## ORIGINAL AD\n{ad}\n\n{report_section}\n\n---\n\n"
    
    pdf.set_font("Arial", 'B', 12)
    pdf.multi_cell(0, 10, f"TARGET AD: {ad.encode('latin-1', 'ignore').decode('latin-1')}")
    pdf.ln(2)
    
    pdf.set_font("Arial", size=10)
    clean_report = report_section.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 7, clean_report)
    
    pdf.ln(10)
    pdf.cell(0, 0, '', 'T')
    pdf.ln(5)

# 5. Saving Files
with open("calibrated_risk_report.md", "w", encoding="utf-8") as f:
    f.write(final_markdown)

pdf.output("Calibrated_Brand_Risk_Report.pdf")

print("\n" + "="*40)
print("SUCCESS: Calibrated reports generated!")
print("="*40)