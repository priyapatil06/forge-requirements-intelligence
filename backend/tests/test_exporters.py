from app.mock_data import build_mock_artifacts
from app.models import ForgeSession
from app.exporters import mermaid_state_machine, openapi_yaml


def test_exporters_are_parseable():
    session = ForgeSession(
        feature_name="Refund Review",
        feature_description="Review refund requests and route exceptions to a supervisor.",
        primary_actor="refund analyst",
    )
    artifacts = build_mock_artifacts(session)
    yaml_text = openapi_yaml(artifacts, session.feature_name)
    mermaid = mermaid_state_machine(artifacts)
    assert "openapi: 3.0.3" in yaml_text
    assert "stateDiagram-v2" in mermaid
    assert "DRAFT --> VALIDATING" in mermaid
