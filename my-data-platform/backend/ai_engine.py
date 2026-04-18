import os

from security import sanitize_for_llm


try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def generate_business_insights(cleaning_stats: list | dict | None, ml_results: dict | None) -> str:
    if OpenAI is None:
        return "AI Insight generation failed: OpenAI package is not installed."

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "AI Insight generation failed: OPENAI_API_KEY is not configured."

    safe_cleaning_stats = sanitize_for_llm(cleaning_stats)
    safe_ml_results = sanitize_for_llm(ml_results)

    prompt = (
        "You are an expert Data Scientist. Write a short, professional business report under 150 words "
        "based on this information. Explain what was cleaned and what model performance means for business impact. "
        f"Data Cleaning Stats: {safe_cleaning_stats}. AutoML Results: {safe_ml_results}."
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You write concise business-facing analytics summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content or "No insight generated."
    except Exception as exc:
        return f"AI Insight generation failed: {exc}"
