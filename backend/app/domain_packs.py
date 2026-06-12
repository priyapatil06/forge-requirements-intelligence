DOMAIN_PACKS: dict[str, dict[str, object]] = {
    "generic": {
        "label": "Generic product",
        "description": "Cross-domain software requirements vocabulary.",
        "glossary": [],
        "rules": [
            "Prefer concrete actor names over the word user.",
            "Do not invent downstream systems or regulatory requirements.",
        ],
    },
    "banking": {
        "label": "Banking and payments",
        "description": "Onboarding, payments, risk, and regulated workflow terminology.",
        "glossary": [
            "KYC: know-your-customer identity verification",
            "AML: anti-money-laundering monitoring",
            "NACHA return code: standardized ACH return reason",
            "maker-checker: dual-control approval pattern",
            "idempotency key: prevents duplicate payment execution",
        ],
        "rules": [
            "Flag missing audit, retention, consent, and reconciliation requirements.",
            "Use explicit payment lifecycle states rather than generic progress states.",
            "Treat money movement as idempotent and failure-recoverable unless stated otherwise.",
        ],
    },
    "support": {
        "label": "Customer support automation",
        "description": "Routing queues, escalation tiers, SLAs, and agent handoffs.",
        "glossary": [
            "triage queue: manual classification queue for uncertain tickets",
            "confidence threshold: score boundary controlling automated action",
            "agent handoff: transfer from automation to a human support agent",
            "SLA breach: service-level response or resolution target exceeded",
        ],
        "rules": [
            "Represent confidence thresholds as explicit business rules.",
            "Include timeout, retry, and escalation states.",
            "Flag any automated customer-facing response without a review policy.",
        ],
    },
    "compliance": {
        "label": "Privacy and compliance",
        "description": "Governance-aware requirements for sensitive data workflows.",
        "glossary": [
            "data subject request: request to access, correct, export, or delete personal data",
            "legal hold: preservation rule that prevents deletion",
            "purpose limitation: use data only for the disclosed purpose",
            "audit trail: immutable record of actions and decisions",
        ],
        "rules": [
            "Flag missing retention, deletion, consent, audit, and access-control details.",
            "Do not assert that a design is legally compliant.",
            "Treat compliance conclusions as requiring qualified human review.",
        ],
    },
}
