export type DomainPack = "generic" | "banking" | "support" | "compliance";

export interface AcceptanceCriterion {
  type: "happy_path" | "edge_case" | "error_handling";
  given: string;
  when: string;
  then: string;
}

export interface UserStory {
  id: string;
  role: string;
  action: string;
  business_value: string;
  acceptance_criteria: AcceptanceCriterion[];
}

export interface ApiField {
  field: string;
  type: string;
  required?: boolean;
  description: string;
}

export interface ApiEndpoint {
  path: string;
  method: string;
  summary: string;
  request_body: ApiField[];
  response_200: ApiField[];
  error_codes: { code: number; meaning: string }[];
}

export interface ArtifactSet {
  summary: string;
  complexity: "low" | "medium" | "high";
  user_stories: UserStory[];
  api_contract: { base_path: string; endpoints: ApiEndpoint[] };
  state_machine: {
    entity: string;
    states: string[];
    initial_state: string;
    terminal_states: string[];
    transitions: { from: string; event: string; to: string; condition?: string | null }[];
  };
  jira_tickets: {
    key: string;
    title: string;
    story: string;
    acceptance_criteria: string[];
    story_points: number;
    type: string;
    labels: string[];
  }[];
  confidence_flags: {
    severity: "warning" | "info";
    field: string;
    message: string;
    suggestion: string;
  }[];
}

export interface ReviewAction {
  id: string;
  decision: string;
  note: string;
  created_at: string;
}

export interface ArtifactRun {
  id: string;
  session_id: string;
  status: string;
  provider: string;
  model: string;
  prompt_version: string;
  artifacts: ArtifactSet;
  latency_ms?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  reviews: ReviewAction[];
}

export interface ForgeSession {
  id: string;
  feature_name: string;
  feature_description: string;
  business_objective: string;
  primary_actor: string;
  data_inputs_outputs: string;
  downstream_dependencies: string;
  edge_cases: string;
  compliance_context: string;
  domain_pack: DomainPack;
  created_at: string;
  updated_at: string;
  runs: ArtifactRun[];
}

export interface IntakeForm {
  feature_name: string;
  feature_description: string;
  business_objective: string;
  primary_actor: string;
  data_inputs_outputs: string;
  downstream_dependencies: string;
  edge_cases: string;
  compliance_context: string;
  domain_pack: DomainPack;
}
