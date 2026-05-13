"""
agent.py

This is the core extraction agent. It uses the Groq API (free!) to read
FNOL documents and pull out the key fields we need for claims processing.

Using Groq because it's completely free for assignments like this — no credit
card needed. Just sign up at console.groq.com and grab an API key.

I used Claude to help me structure the prompt and figure out the JSON schema.
Honestly made the extraction part way easier than doing regex manually.
"""

import json
from groq import Groq

# these are all the fields we need to extract from each FNOL document
# keeping them in one place so it's easy to update later
REQUIRED_FIELDS = {
    "policy_information": [
        "policy_number",
        "policyholder_name",
        "policy_effective_date",
        "policy_expiry_date"
    ],
    "incident_information": [
        "date_of_incident",
        "time_of_incident",
        "location",
        "description"
    ],
    "involved_parties": [
        "claimant",
        "third_parties",
        "contact_details"
    ],
    "asset_details": [
        "asset_type",
        "asset_id",
        "estimated_damage"
    ],
    "claim_details": [
        "claim_type",
        "attachments",
        "initial_estimate"
    ]
}


def extract_fields_with_llm(document_text: str) -> dict:
    """
    Sends the FNOL document to Groq (using llama-3.1-8b-instant) and asks it
    to extract all fields. Returns a dict with all extracted info.

    Groq is free — sign up at console.groq.com to get your API key.
    Set it as: export GROQ_API_KEY=your_key_here
    """
    client = Groq()  # auto-reads GROQ_API_KEY from environment

    system_prompt = """You are an insurance claims processing assistant.
Your job is to extract structured information from FNOL (First Notice of Loss) documents.

You MUST respond with ONLY valid JSON and nothing else — no explanation, no markdown, no backticks.

Extract the following fields and return them in this exact JSON structure:

{
  "policy_information": {
    "policy_number": "...",
    "policyholder_name": "...",
    "policy_effective_date": "...",
    "policy_expiry_date": "..."
  },
  "incident_information": {
    "date_of_incident": "...",
    "time_of_incident": "...",
    "location": "...",
    "description": "..."
  },
  "involved_parties": {
    "claimant": "...",
    "third_parties": "...",
    "contact_details": "..."
  },
  "asset_details": {
    "asset_type": "...",
    "asset_id": "...",
    "estimated_damage": "..."
  },
  "claim_details": {
    "claim_type": "...",
    "attachments": "...",
    "initial_estimate": "..."
  }
}

Rules:
- If a field is clearly missing, not provided, or marked as [NOT PROVIDED] / [NONE], set it to null.
- For estimated_damage and initial_estimate, extract the numeric value only (e.g., 8500) if possible, else keep as string.
- For third_parties, list all third parties separated by semicolons if multiple.
- For attachments, list all attachment names separated by commas if multiple, else null.
- Do not guess or fill in information that isn't there.
"""

    user_prompt = f"""Please extract all fields from this FNOL document:

{document_text}
"""

    # call the Groq API — same interface as OpenAI
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # fast + free on Groq
        max_tokens=1000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    raw_response = response.choices[0].message.content.strip()

    # LLMs sometimes add backticks even when told not to, strip just in case
    if raw_response.startswith("```"):
        raw_response = raw_response.split("```")[1]
        if raw_response.startswith("json"):
            raw_response = raw_response[4:].strip()

    extracted = json.loads(raw_response)
    return extracted


def find_missing_fields(extracted: dict) -> list:
    """
    Goes through all the extracted fields and figures out which ones are null/missing.
    Returns a flat list of missing field names like ["time_of_incident", "attachments"]
    """
    missing = []

    for section, fields in REQUIRED_FIELDS.items():
        section_data = extracted.get(section, {})
        for field in fields:
            value = section_data.get(field)
            # null, empty string, or literally "N/A" all count as missing
            if value is None or value == "" or (isinstance(value, str) and value.strip().upper() in ["N/A", "NONE", "NOT PROVIDED", "NULL"]):
                missing.append(field)

    return missing
