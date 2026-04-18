import json
import os
import re

import polars as pl
from security import mask_sensitive_data, sanitize_for_llm

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def _extract_json(text: str) -> dict:
    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "", 1).replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def identify_dataset_semantics(dataframe: pl.DataFrame) -> dict:
    if OpenAI is None:
        return {
            "domain": "Unknown",
            "confidence": 0,
            "columns": [],
            "error": "OpenAI package is not installed.",
        }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "domain": "Unknown",
            "confidence": 0,
            "columns": [],
            "error": "OPENAI_API_KEY is not configured.",
        }

    secure_dataframe = mask_sensitive_data(dataframe)
    sample_data = sanitize_for_llm(secure_dataframe.head(5).to_dicts())
    column_names = dataframe.columns

    prompt = f"""
You are an expert Data Architect.

Analyze this tabular sample:
{sample_data}

Column names:
{column_names}

Tasks:
1. Identify the most likely business domain (Retail, Finance, Healthcare, HR, Logistics, Marketing, Generic).
2. For each column, assign a semantic_type such as Product Name, Currency, Date, Email, ID, Category, Quantity, Region.
3. Return only valid JSON using this exact shape:
{{
  "domain": "Retail",
  "confidence": 92,
  "columns": [
    {{"name": "column_name", "semantic_type": "Product Name", "confidence": 88}}
  ]
}}
"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are strict about returning valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        text = response.choices[0].message.content or "{}"
        semantics = _extract_json(text)

        if "columns" not in semantics or not isinstance(semantics.get("columns"), list):
            semantics["columns"] = []
        if "domain" not in semantics:
            semantics["domain"] = "Generic"
        if "confidence" not in semantics:
            semantics["confidence"] = 0

        return semantics
    except Exception as exc:
        return {
            "domain": "Unknown",
            "confidence": 0,
            "columns": [],
            "error": f"Domain identification failed: {exc}",
        }
