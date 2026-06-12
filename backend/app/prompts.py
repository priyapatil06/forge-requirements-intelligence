import json

from app.domain_packs import DOMAIN_PACKS
from app.models import ForgeSession
from app.schemas import ArtifactSet

PROMPT_VERSION = "1.0"


def build_system_prompt(domain_pack: str) -> str:
    pack = DOMAIN_PACKS.get(domain_pack, DOMAIN_PACKS["generic"])
    schema = ArtifactSet.model_json_schema(by_alias=True)
    glossary = "\n".join(f"- {item}" for item in pack["glossary"]) or "- None"
    rules = "\n".join(f"- {item}" for item in pack["rules"])
    return f"""
You are Forge, a requirements intelligence engine. Your output will be reviewed by product and engineering teams before use. Accuracy, traceability, and explicit uncertainty are more important than producing a complete-looking answer.

Return ONLY one valid JSON object that conforms to the supplied JSON Schema. Do not wrap it in markdown. Do not include analysis, hidden reasoning, commentary, or extra keys.

Requirements:
- Derive actors, rules, fields, states, and tickets from the intake.
- Do not invent named systems, regulations, data fields, or business rules.
- When information is missing, choose the safest neutral scaffold and add a confidence flag.
- Each user story must have at least one happy path, one edge case, and one error-handling criterion.
- API output is a scaffold, not an implementation guarantee.
- State transitions must reference states listed in the state array.
- JIRA story points are tentative and must be flagged when complexity information is weak.
- Never claim legal, security, or regulatory compliance.

Domain pack: {pack['label']}
Domain glossary:
{glossary}

Domain rules:
{rules}

JSON Schema:
{json.dumps(schema, ensure_ascii=False)}
""".strip()


def build_user_prompt(session: ForgeSession) -> str:
    return f"""
Create a coherent artifact set for the following feature intake. Preserve traceability to the supplied facts and use confidence flags for gaps.

FEATURE NAME
{session.feature_name}

NATURAL-LANGUAGE DESCRIPTION
{session.feature_description}

BUSINESS OBJECTIVE
{session.business_objective or '[not provided]'}

PRIMARY ACTOR
{session.primary_actor or '[not provided]'}

DATA INPUTS AND OUTPUTS
{session.data_inputs_outputs or '[not provided]'}

DOWNSTREAM SYSTEM DEPENDENCIES
{session.downstream_dependencies or '[not provided]'}

EDGE CASES AND ERROR CONDITIONS
{session.edge_cases or '[not provided]'}

COMPLIANCE OR GOVERNANCE CONTEXT
{session.compliance_context or '[not provided]'}
""".strip()
