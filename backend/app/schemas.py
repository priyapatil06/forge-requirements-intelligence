from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DomainPack(str, Enum):
    generic = "generic"
    banking = "banking"
    support = "support"
    compliance = "compliance"


class AcceptanceCriterion(BaseModel):
    type: Literal["happy_path", "edge_case", "error_handling"]
    given: str = Field(min_length=1)
    when: str = Field(min_length=1)
    then: str = Field(min_length=1)


class UserStory(BaseModel):
    id: str
    role: str
    action: str
    business_value: str
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=3)


class ApiField(BaseModel):
    field: str
    type: Literal["string", "number", "integer", "boolean", "object", "array"]
    required: bool = False
    description: str


class ApiResponseField(BaseModel):
    field: str
    type: Literal["string", "number", "integer", "boolean", "object", "array"]
    description: str


class ApiError(BaseModel):
    code: int
    meaning: str


class ApiEndpoint(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    summary: str
    request_body: list[ApiField] = Field(default_factory=list)
    response_200: list[ApiResponseField] = Field(default_factory=list)
    error_codes: list[ApiError] = Field(default_factory=list)


class ApiContract(BaseModel):
    base_path: str = "/api/v1"
    endpoints: list[ApiEndpoint] = Field(min_length=1)


class StateTransition(BaseModel):
    from_state: str = Field(alias="from")
    event: str
    to: str
    condition: str | None = None

    model_config = ConfigDict(populate_by_name=True)


class StateMachine(BaseModel):
    entity: str
    states: list[str] = Field(min_length=2)
    initial_state: str
    terminal_states: list[str] = Field(min_length=1)
    transitions: list[StateTransition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "StateMachine":
        state_set = set(self.states)
        if self.initial_state not in state_set:
            raise ValueError("initial_state must appear in states")
        if not set(self.terminal_states).issubset(state_set):
            raise ValueError("terminal_states must appear in states")
        for transition in self.transitions:
            if transition.from_state not in state_set or transition.to not in state_set:
                raise ValueError("transition states must appear in states")
        return self


class JiraTicket(BaseModel):
    key: str
    title: str
    story: str
    acceptance_criteria: list[str] = Field(min_length=1)
    story_points: int = Field(ge=1, le=13)
    type: Literal["Story", "Task", "Bug"] = "Story"
    labels: list[str] = Field(default_factory=list)


class ConfidenceFlag(BaseModel):
    severity: Literal["warning", "info"]
    field: str
    message: str
    suggestion: str


class ArtifactSet(BaseModel):
    summary: str
    complexity: Literal["low", "medium", "high"]
    user_stories: list[UserStory] = Field(min_length=1)
    api_contract: ApiContract
    state_machine: StateMachine
    jira_tickets: list[JiraTicket] = Field(min_length=1)
    confidence_flags: list[ConfidenceFlag] = Field(default_factory=list)


class ForgeSessionCreate(BaseModel):
    feature_name: str = Field(min_length=2, max_length=200)
    feature_description: str = Field(min_length=20, max_length=30000)
    business_objective: str = Field(default="", max_length=5000)
    primary_actor: str = Field(default="", max_length=500)
    data_inputs_outputs: str = Field(default="", max_length=5000)
    downstream_dependencies: str = Field(default="", max_length=5000)
    edge_cases: str = Field(default="", max_length=5000)
    compliance_context: str = Field(default="", max_length=5000)
    domain_pack: DomainPack = DomainPack.generic


class ForgeSessionUpdate(BaseModel):
    feature_name: str | None = Field(default=None, min_length=2, max_length=200)
    feature_description: str | None = Field(default=None, min_length=20, max_length=30000)
    business_objective: str | None = Field(default=None, max_length=5000)
    primary_actor: str | None = Field(default=None, max_length=500)
    data_inputs_outputs: str | None = Field(default=None, max_length=5000)
    downstream_dependencies: str | None = Field(default=None, max_length=5000)
    edge_cases: str | None = Field(default=None, max_length=5000)
    compliance_context: str | None = Field(default=None, max_length=5000)
    domain_pack: DomainPack | None = None


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    decision: str
    note: str
    created_at: datetime


class ArtifactRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    session_id: str
    status: str
    provider: str
    model: str
    prompt_version: str
    artifacts: ArtifactSet
    latency_ms: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    reviews: list[ReviewRead] = Field(default_factory=list)


class ForgeSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    feature_name: str
    feature_description: str
    business_objective: str
    primary_actor: str
    data_inputs_outputs: str
    downstream_dependencies: str
    edge_cases: str
    compliance_context: str
    domain_pack: str
    created_at: datetime
    updated_at: datetime
    runs: list[ArtifactRunRead] = Field(default_factory=list)


class ArtifactUpdate(BaseModel):
    artifacts: ArtifactSet


class ReviewActionCreate(BaseModel):
    decision: Literal["approved", "changes_requested", "comment"]
    note: str = Field(default="", max_length=5000)


class JiraFieldMapping(BaseModel):
    project_key: str = Field(min_length=1, max_length=30)
    story_issue_type: str = "Story"
    task_issue_type: str = "Task"
    bug_issue_type: str = "Bug"
    create_epic: bool = False
    epic_issue_type: str = "Epic"
    epic_name_field: str | None = None
    parent_field: str = "parent"
    story_points_field: str | None = None
    labels: list[str] = Field(default_factory=lambda: ["forge-generated"])


class JiraSyncRequest(BaseModel):
    connection_id: str
    mapping: JiraFieldMapping


class JiraSyncResult(BaseModel):
    created_issues: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
