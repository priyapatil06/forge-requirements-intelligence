from app.models import ForgeSession
from app.schemas import ArtifactSet


def build_mock_artifacts(session: ForgeSession) -> ArtifactSet:
    actor = (session.primary_actor or "").strip() or "product operations analyst"
    feature = (session.feature_name or "Untitled feature").strip()
    flags = []
    if not (session.business_objective or "").strip():
        flags.append({
            "severity": "warning",
            "field": "business_objective",
            "message": "No measurable success outcome was provided.",
            "suggestion": "Add a target such as reduced handling time, lower error rate, or improved conversion.",
        })
    if not (session.downstream_dependencies or "").strip():
        flags.append({
            "severity": "warning",
            "field": "downstream_dependencies",
            "message": "No downstream systems or failure behavior were specified.",
            "suggestion": "Identify called systems, timeout behavior, retry policy, and ownership.",
        })
    if not (session.compliance_context or "").strip():
        flags.append({
            "severity": "info",
            "field": "compliance_context",
            "message": "No compliance or governance constraints were supplied.",
            "suggestion": "Confirm whether audit, retention, consent, privacy, or access-control requirements apply.",
        })

    payload = {
        "summary": f"Provide a controlled workflow for {feature.lower()} with explicit validation, review, and failure handling.",
        "complexity": "medium",
        "user_stories": [
            {
                "id": "US-01",
                "role": actor,
                "action": f"submit the required inputs for {feature.lower()}",
                "business_value": "the workflow begins with complete and traceable information",
                "acceptance_criteria": [
                    {
                        "type": "happy_path",
                        "given": "all required inputs are present and valid",
                        "when": "the actor submits the request",
                        "then": "the system creates a request and returns a stable identifier",
                    },
                    {
                        "type": "edge_case",
                        "given": "an optional field is omitted",
                        "when": "the actor submits the request",
                        "then": "the system continues without inventing a value for the omitted field",
                    },
                    {
                        "type": "error_handling",
                        "given": "a required input is missing or malformed",
                        "when": "the actor submits the request",
                        "then": "the system rejects the request with field-level validation details",
                    },
                ],
            },
            {
                "id": "US-02",
                "role": "reviewer",
                "action": "review generated decisions and surfaced assumptions",
                "business_value": "automation does not bypass accountable human judgment",
                "acceptance_criteria": [
                    {
                        "type": "happy_path",
                        "given": "a generated result is available",
                        "when": "the reviewer opens the result",
                        "then": "the system displays the output and all confidence flags together",
                    },
                    {
                        "type": "edge_case",
                        "given": "the result contains a low-confidence assumption",
                        "when": "the reviewer requests changes",
                        "then": "the system records the review note without marking the result approved",
                    },
                    {
                        "type": "error_handling",
                        "given": "the result cannot be loaded",
                        "when": "the reviewer opens the result",
                        "then": "the system preserves the prior state and provides a retryable error",
                    },
                ],
            },
            {
                "id": "US-03",
                "role": "delivery lead",
                "action": "export approved artifacts to the delivery toolchain",
                "business_value": "engineering receives a consistent, reviewable starting point",
                "acceptance_criteria": [
                    {
                        "type": "happy_path",
                        "given": "the artifact set has been reviewed",
                        "when": "the lead exports it",
                        "then": "the system provides valid JSON, OpenAPI YAML, and Mermaid outputs",
                    },
                    {
                        "type": "edge_case",
                        "given": "a project uses custom Jira fields",
                        "when": "the lead configures field mapping",
                        "then": "the system uses the supplied field IDs instead of assuming defaults",
                    },
                    {
                        "type": "error_handling",
                        "given": "the downstream tool rejects an export",
                        "when": "synchronization fails",
                        "then": "the system reports the failing item and does not claim a successful sync",
                    },
                ],
            },
        ],
        "api_contract": {
            "base_path": "/api/v1",
            "endpoints": [
                {
                    "path": "/requests",
                    "method": "POST",
                    "summary": f"Create a {feature} request",
                    "request_body": [
                        {
                            "field": "feature_input",
                            "type": "object",
                            "required": True,
                            "description": "Validated business input required to start the workflow",
                        },
                        {
                            "field": "idempotency_key",
                            "type": "string",
                            "required": False,
                            "description": "Optional key used to prevent duplicate request creation",
                        },
                    ],
                    "response_200": [
                        {"field": "request_id", "type": "string", "description": "Stable request identifier"},
                        {"field": "status", "type": "string", "description": "Initial workflow state"},
                    ],
                    "error_codes": [
                        {"code": 400, "meaning": "Input validation failed"},
                        {"code": 409, "meaning": "A request with the same idempotency key already exists"},
                        {"code": 503, "meaning": "A required downstream dependency is unavailable"},
                    ],
                },
                {
                    "path": "/requests/{request_id}/review",
                    "method": "POST",
                    "summary": "Record a human review decision",
                    "request_body": [
                        {"field": "decision", "type": "string", "required": True, "description": "approve or request_changes"},
                        {"field": "note", "type": "string", "required": False, "description": "Reviewer rationale"},
                    ],
                    "response_200": [
                        {"field": "request_id", "type": "string", "description": "Reviewed request identifier"},
                        {"field": "status", "type": "string", "description": "Updated workflow state"},
                    ],
                    "error_codes": [
                        {"code": 404, "meaning": "Request was not found"},
                        {"code": 409, "meaning": "The request is not in a reviewable state"},
                    ],
                },
            ],
        },
        "state_machine": {
            "entity": "feature_request",
            "states": ["DRAFT", "VALIDATING", "NEEDS_REVIEW", "APPROVED", "CHANGES_REQUESTED", "FAILED"],
            "initial_state": "DRAFT",
            "terminal_states": ["APPROVED", "FAILED"],
            "transitions": [
                {"from": "DRAFT", "event": "submit", "to": "VALIDATING", "condition": "required inputs present"},
                {"from": "VALIDATING", "event": "validation_passed", "to": "NEEDS_REVIEW", "condition": None},
                {"from": "VALIDATING", "event": "validation_failed", "to": "FAILED", "condition": "non-retryable input error"},
                {"from": "NEEDS_REVIEW", "event": "approve", "to": "APPROVED", "condition": "reviewer has approval permission"},
                {"from": "NEEDS_REVIEW", "event": "request_changes", "to": "CHANGES_REQUESTED", "condition": None},
                {"from": "CHANGES_REQUESTED", "event": "resubmit", "to": "VALIDATING", "condition": "requested changes addressed"},
            ],
        },
        "jira_tickets": [
            {
                "key": "FORGE-001",
                "title": f"Capture validated inputs for {feature}",
                "story": f"As a {actor}, I want to submit validated inputs so that the workflow starts with complete information.",
                "acceptance_criteria": [
                    "Required fields are validated before persistence.",
                    "The response includes a stable request identifier.",
                    "Validation errors identify the affected field.",
                ],
                "story_points": 5,
                "type": "Story",
                "labels": ["capture", "validation"],
            },
            {
                "key": "FORGE-002",
                "title": "Add human review and confidence flags",
                "story": "As a reviewer, I want assumptions displayed with the output so that I can make an informed approval decision.",
                "acceptance_criteria": [
                    "Warnings and informational flags are visually distinct.",
                    "Review decisions are stored with a timestamp and note.",
                    "A changes-requested run is not presented as approved.",
                ],
                "story_points": 5,
                "type": "Story",
                "labels": ["review", "governance"],
            },
            {
                "key": "FORGE-003",
                "title": "Export reviewed artifacts",
                "story": "As a delivery lead, I want standard export formats so that approved artifacts can enter existing engineering tools.",
                "acceptance_criteria": [
                    "OpenAPI output parses as YAML.",
                    "Mermaid output contains every state transition.",
                    "The JSON bundle includes intake, artifacts, and run metadata.",
                ],
                "story_points": 3,
                "type": "Task",
                "labels": ["export", "integration"],
            },
        ],
        "confidence_flags": flags,
    }
    return ArtifactSet.model_validate(payload)
