def sample_session():
    return {
        "feature_name": "AI Ticket Routing",
        "feature_description": "Classify incoming support tickets, route high-confidence tickets automatically, and send uncertain tickets to human triage.",
        "business_objective": "Reduce median routing time while preserving escalation quality.",
        "primary_actor": "customer support operations manager",
        "data_inputs_outputs": "Input: ticket text and account tier. Output: category, confidence score, route, and audit event.",
        "downstream_dependencies": "Knowledge base, queue service, CRM, and audit log.",
        "edge_cases": "VIP accounts require review. Low confidence goes to triage. Queue outage must not lose the ticket.",
        "compliance_context": "Retain routing decisions for audit and restrict access to ticket text.",
        "domain_pack": "support",
    }


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["mock_llm"] is True


def test_complete_mock_workflow(client):
    created = client.post("/api/v1/sessions", json=sample_session())
    assert created.status_code == 201
    session_id = created.json()["id"]

    generated = client.post(f"/api/v1/sessions/{session_id}/generate")
    assert generated.status_code == 201
    body = generated.json()
    assert len(body["artifacts"]["user_stories"]) >= 3
    assert body["provider"] == "mock"

    run_id = body["id"]
    reviewed = client.post(
        f"/api/v1/runs/{run_id}/review",
        json={"decision": "approved", "note": "Reviewed in test."},
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["status"] == "approved"

    exported = client.get(f"/api/v1/runs/{run_id}/export?format=openapi")
    assert exported.status_code == 200
    assert "openapi: 3.0.3" in exported.text


def test_invalid_artifact_edit_is_rejected(client):
    created = client.post("/api/v1/sessions", json=sample_session()).json()
    run = client.post(f"/api/v1/sessions/{created['id']}/generate").json()
    response = client.put(f"/api/v1/runs/{run['id']}", json={"artifacts": {"summary": "bad"}})
    assert response.status_code == 422
