import type { ArtifactRun, ForgeSession, IntakeForm } from "./types";

export const blankIntake: IntakeForm = {
  feature_name: "",
  feature_description: "",
  business_objective: "",
  primary_actor: "",
  data_inputs_outputs: "",
  downstream_dependencies: "",
  edge_cases: "",
  compliance_context: "",
  domain_pack: "generic",
};

export function latestRun(session: ForgeSession): ArtifactRun | undefined {
  return [...session.runs].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
}

export function canGenerate(form: IntakeForm) {
  return form.feature_name.trim().length >= 2 && form.feature_description.trim().length >= 20;
}
