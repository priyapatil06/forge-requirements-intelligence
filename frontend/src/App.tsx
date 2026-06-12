import { useEffect, useMemo, useState } from "react";
import { api, exportUrl } from "./api";
import type { ArtifactRun, ForgeSession, IntakeForm, UserStory } from "./types";
import { blankIntake, canGenerate, latestRun } from "./utils";

const example: IntakeForm = {
  feature_name: "AI Ticket Routing and Response System",
  feature_description:
    "When a customer submits a support ticket, classify it as billing, technical, account, or general. Route above 85% confidence automatically, require agent review from 60–85%, and send lower-confidence tickets to triage. Generate a knowledge-base-backed draft for high-confidence tickets. VIP accounts always require review. Cancellation, refund, or legal language triggers escalation. Escalate unanswered tickets after two hours and after three failed resolution attempts.",
  business_objective:
    "Reduce median routing time and repetitive drafting work without lowering escalation quality or agent accountability.",
  primary_actor: "customer support operations manager and support agent",
  data_inputs_outputs:
    "Inputs: ticket text, customer tier, account metadata, queue availability, and prior resolution attempts. Outputs: category, confidence score, routing decision, draft response, escalation reason, and audit event.",
  downstream_dependencies:
    "Customer support platform, knowledge base, queue service, CRM account tier, notification service, and audit log.",
  edge_cases:
    "VIP customers always require review. Low confidence goes to triage. Sensitive keywords trigger immediate escalation. Queue outages must preserve the ticket. Draft generation failures must not block routing.",
  compliance_context:
    "Restrict access to ticket text, retain routing decisions for audit, and avoid sending AI-generated responses without an agent-approved policy.",
  domain_pack: "support",
};

type Tab = "stories" | "api" | "state" | "jira" | "flags" | "json" | "delivery";

function Field({
  label,
  value,
  onChange,
  placeholder,
  rows = 3,
  hint,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  rows?: number;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea rows={rows} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
      {hint && <small>{hint}</small>}
    </label>
  );
}

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function StoryCard({ story }: { story: UserStory }) {
  const [open, setOpen] = useState(true);
  return (
    <article className="artifact-card">
      <button className="artifact-title" onClick={() => setOpen(!open)}>
        <Badge tone="blue">{story.id}</Badge>
        <strong>
          As a {story.role}, I want to {story.action}
        </strong>
        <span>{open ? "−" : "+"}</span>
      </button>
      {open && (
        <div className="artifact-body">
          <p><b>Business value:</b> {story.business_value}</p>
          {story.acceptance_criteria.map((criterion, index) => (
            <div className={`criterion criterion-${criterion.type}`} key={`${story.id}-${index}`}>
              <Badge tone={criterion.type === "happy_path" ? "green" : criterion.type === "edge_case" ? "amber" : "red"}>
                {criterion.type.replace("_", " ")}
              </Badge>
              <p><b>Given</b> {criterion.given}</p>
              <p><b>When</b> {criterion.when}</p>
              <p><b>Then</b> {criterion.then}</p>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function ArtifactReview({
  session,
  run,
  onRunChanged,
}: {
  session: ForgeSession;
  run: ArtifactRun;
  onRunChanged: (run: ArtifactRun) => void;
}) {
  const [tab, setTab] = useState<Tab>("stories");
  const [jsonText, setJsonText] = useState(JSON.stringify(run.artifacts, null, 2));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [jira, setJira] = useState<{ configured: boolean; connections: { id: string; site_name: string }[] }>({ configured: false, connections: [] });
  const [jiraConnection, setJiraConnection] = useState("");
  const [jiraProject, setJiraProject] = useState("");
  const [storyPointsField, setStoryPointsField] = useState("");

  useEffect(() => {
    setJsonText(JSON.stringify(run.artifacts, null, 2));
  }, [run]);

  useEffect(() => {
    api.jiraStatus().then((status) => {
      setJira(status);
      if (status.connections[0]) setJiraConnection(status.connections[0].id);
    }).catch(() => undefined);
  }, []);

  async function review(decision: "approved" | "changes_requested" | "comment") {
    setBusy(true);
    setMessage("");
    try {
      const updated = await api.review(run.id, decision, note);
      onRunChanged(updated);
      setNote("");
      setMessage("Review action saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Review failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveJson() {
    setBusy(true);
    setMessage("");
    try {
      const parsed = JSON.parse(jsonText);
      const updated = await api.updateArtifacts(run.id, parsed);
      onRunChanged(updated);
      setMessage("Artifact JSON validated and saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Invalid JSON.");
    } finally {
      setBusy(false);
    }
  }

  async function connectJira() {
    try {
      const result = await api.jiraStart();
      window.location.href = result.authorization_url;
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Jira setup failed.");
    }
  }

  async function syncJira() {
    if (!jiraConnection || !jiraProject) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await api.jiraSync(run.id, {
        connection_id: jiraConnection,
        mapping: {
          project_key: jiraProject,
          story_issue_type: "Story",
          task_issue_type: "Task",
          bug_issue_type: "Bug",
          create_epic: false,
          parent_field: "parent",
          story_points_field: storyPointsField || null,
          labels: ["forge-generated"],
        },
      });
      setMessage(`Created ${result.created_issues.length} Jira issue(s). ${result.warnings.join(" ")}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Jira sync failed.");
    } finally {
      setBusy(false);
    }
  }

  const artifacts = run.artifacts;
  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "stories", label: "User stories", count: artifacts.user_stories.length },
    { id: "api", label: "API contract", count: artifacts.api_contract.endpoints.length },
    { id: "state", label: "State machine", count: artifacts.state_machine.transitions.length },
    { id: "jira", label: "JIRA tickets", count: artifacts.jira_tickets.length },
    { id: "flags", label: "Confidence flags", count: artifacts.confidence_flags.length },
    { id: "json", label: "Edit JSON" },
    { id: "delivery", label: "Review & deliver" },
  ];

  return (
    <section className="review">
      <div className="summary-card">
        <div>
          <div className="eyebrow">Generated artifact set</div>
          <h2>{session.feature_name}</h2>
          <p>{artifacts.summary}</p>
        </div>
        <div className="summary-meta">
          <Badge tone={artifacts.complexity === "high" ? "red" : artifacts.complexity === "medium" ? "amber" : "green"}>{artifacts.complexity}</Badge>
          <Badge tone="blue">{run.model}</Badge>
          <Badge tone={run.status === "approved" ? "green" : "neutral"}>{run.status}</Badge>
        </div>
      </div>

      <div className="tabs">
        {tabs.map((item) => (
          <button key={item.id} className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)}>
            {item.label}{item.count !== undefined && <em>{item.count}</em>}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tab === "stories" && artifacts.user_stories.map((story) => <StoryCard story={story} key={story.id} />)}

        {tab === "api" && artifacts.api_contract.endpoints.map((endpoint) => (
          <article className="artifact-card" key={`${endpoint.method}-${endpoint.path}`}>
            <div className="api-line"><Badge tone="purple">{endpoint.method}</Badge><code>{artifacts.api_contract.base_path}{endpoint.path}</code><strong>{endpoint.summary}</strong></div>
            <div className="artifact-body two-column">
              <div><h4>Request</h4>{endpoint.request_body.map((field) => <p key={field.field}><code>{field.field}</code> · {field.type}{field.required ? " · required" : ""}<br/><small>{field.description}</small></p>)}</div>
              <div><h4>Response</h4>{endpoint.response_200.map((field) => <p key={field.field}><code>{field.field}</code> · {field.type}<br/><small>{field.description}</small></p>)}</div>
            </div>
          </article>
        ))}

        {tab === "state" && (
          <div>
            <div className="state-list">{artifacts.state_machine.states.map((state) => <Badge key={state} tone={artifacts.state_machine.terminal_states.includes(state) ? "green" : state === artifacts.state_machine.initial_state ? "blue" : "neutral"}>{state}</Badge>)}</div>
            <table><thead><tr><th>From</th><th>Event</th><th>To</th><th>Condition</th></tr></thead><tbody>{artifacts.state_machine.transitions.map((transition, index) => <tr key={index}><td><code>{transition.from}</code></td><td>{transition.event}</td><td><code>{transition.to}</code></td><td>{transition.condition || "—"}</td></tr>)}</tbody></table>
          </div>
        )}

        {tab === "jira" && artifacts.jira_tickets.map((ticket) => (
          <article className="artifact-card" key={ticket.key}>
            <div className="api-line"><code>{ticket.key}</code><Badge tone="blue">{ticket.type}</Badge><strong>{ticket.title}</strong><Badge>{ticket.story_points} pts</Badge></div>
            <div className="artifact-body"><p><i>{ticket.story}</i></p><ul>{ticket.acceptance_criteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ul></div>
          </article>
        ))}

        {tab === "flags" && (
          <div>{artifacts.confidence_flags.length === 0 ? <div className="empty">No flags were generated. A human review is still required.</div> : artifacts.confidence_flags.map((flag, index) => <article className={`flag flag-${flag.severity}`} key={index}><div><Badge tone={flag.severity === "warning" ? "amber" : "blue"}>{flag.severity}</Badge><code>{flag.field}</code></div><strong>{flag.message}</strong><p><b>Resolve:</b> {flag.suggestion}</p></article>)}</div>
        )}

        {tab === "json" && (
          <div><p className="muted">Edit the full artifact set. The backend rejects JSON that does not match the required schema.</p><textarea className="json-editor" value={jsonText} onChange={(e) => setJsonText(e.target.value)} /><button className="primary" disabled={busy} onClick={saveJson}>Validate and save</button></div>
        )}

        {tab === "delivery" && (
          <div className="delivery-grid">
            <article className="panel">
              <h3>Human review</h3>
              <textarea rows={4} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Record rationale, requested changes, or remaining risks." />
              <div className="button-row"><button disabled={busy} onClick={() => review("comment")}>Add comment</button><button className="danger-outline" disabled={busy} onClick={() => review("changes_requested")}>Request changes</button><button className="primary" disabled={busy} onClick={() => review("approved")}>Approve</button></div>
              {run.reviews.length > 0 && <div className="review-log"><h4>Audit log</h4>{run.reviews.map((item) => <p key={item.id}><Badge tone={item.decision === "approved" ? "green" : item.decision === "changes_requested" ? "amber" : "neutral"}>{item.decision}</Badge> {item.note || "No note"}</p>)}</div>}
            </article>
            <article className="panel">
              <h3>Exports</h3>
              <p className="muted">Downloads are generated from the validated, saved artifact set.</p>
              <div className="download-list"><a href={exportUrl(run.id, "json")}>Structured JSON</a><a href={exportUrl(run.id, "openapi")}>OpenAPI YAML</a><a href={exportUrl(run.id, "mermaid")}>Mermaid state diagram</a><a href={exportUrl(run.id, "zip")}>Complete ZIP bundle</a></div>
            </article>
            <article className="panel jira-panel">
              <h3>Jira Cloud</h3>
              {!jira.configured ? <><p className="muted">Add Atlassian OAuth credentials to the backend environment before connecting.</p><button disabled>Connect Jira</button></> : jira.connections.length === 0 ? <button className="primary" onClick={connectJira}>Connect Jira</button> : <>
                <label>Connection<select value={jiraConnection} onChange={(e) => setJiraConnection(e.target.value)}>{jira.connections.map((connection) => <option value={connection.id} key={connection.id}>{connection.site_name}</option>)}</select></label>
                <label>Project key<input value={jiraProject} onChange={(e) => setJiraProject(e.target.value.toUpperCase())} placeholder="e.g. FORGE" /></label>
                <label>Story points field ID (optional)<input value={storyPointsField} onChange={(e) => setStoryPointsField(e.target.value)} placeholder="e.g. customfield_10016" /></label>
                <button className="primary" disabled={busy || !jiraProject} onClick={syncJira}>Create Jira issues</button>
              </>}
            </article>
          </div>
        )}
      </div>
      {message && <div className="message">{message}</div>}
    </section>
  );
}

export default function App() {
  const [sessions, setSessions] = useState<ForgeSession[]>([]);
  const [selected, setSelected] = useState<ForgeSession | null>(null);
  const [form, setForm] = useState<IntakeForm>(example);
  const [run, setRun] = useState<ArtifactRun | null>(null);
  const [mockMode, setMockMode] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refreshSessions(preferId?: string) {
    const rows = await api.listSessions();
    setSessions(rows);
    if (preferId) {
      const match = rows.find((item) => item.id === preferId);
      if (match) setSelected(match);
    }
  }

  useEffect(() => {
    api.health().then((result) => setMockMode(result.mock_llm)).catch(() => setError("Backend is not reachable."));
    refreshSessions().catch(() => undefined);
  }, []);

  const selectedLatestRun = useMemo(() => (selected ? latestRun(selected) : undefined), [selected]);

  function selectSession(session: ForgeSession) {
    setSelected(session);
    setForm({
      feature_name: session.feature_name,
      feature_description: session.feature_description,
      business_objective: session.business_objective,
      primary_actor: session.primary_actor,
      data_inputs_outputs: session.data_inputs_outputs,
      downstream_dependencies: session.downstream_dependencies,
      edge_cases: session.edge_cases,
      compliance_context: session.compliance_context,
      domain_pack: session.domain_pack,
    });
    setRun(latestRun(session) ?? null);
    setError("");
  }

  function newSession() {
    setSelected(null);
    setRun(null);
    setForm(blankIntake);
    setError("");
  }

  async function generate() {
    setBusy(true);
    setError("");
    try {
      const session = selected ? await api.updateSession(selected.id, form) : await api.createSession(form);
      const generated = await api.generate(session.id);
      setSelected({ ...session, runs: [...session.runs, generated] });
      setRun(generated);
      await refreshSessions(session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setBusy(false);
    }
  }

  function updateField<K extends keyof IntakeForm>(key: K, value: IntakeForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span>Forge</span><small>Requirements Intelligence</small></div>
        <div className="topbar-meta"><Badge tone={mockMode ? "amber" : "green"}>{mockMode ? "DEMO / MOCK LLM" : "CLAUDE API"}</Badge><a href="https://github.com/" target="_blank" rel="noreferrer">GitHub repository</a></div>
      </header>

      <aside className="sidebar">
        <button className="primary new-button" onClick={newSession}>＋ New feature</button>
        <div className="sidebar-title">History</div>
        {sessions.length === 0 && <p className="muted">No saved sessions yet.</p>}
        {sessions.map((session) => {
          const last = latestRun(session);
          return <button className={`history-item ${selected?.id === session.id ? "selected" : ""}`} key={session.id} onClick={() => selectSession(session)}><strong>{session.feature_name}</strong><span>{session.domain_pack} · {last?.status ?? "draft"}</span></button>;
        })}
      </aside>

      <main>
        {error && <div className="error-box">{error}</div>}
        {!run ? (
          <section className="capture">
            <div className="page-heading"><div><div className="eyebrow">Stage 1 · Capture</div><h1>Describe the feature and expose its gaps.</h1><p>Free text alone hides assumptions. These fields preserve the business and delivery context that engineering artifacts need.</p></div><button onClick={() => setForm(example)}>Load example</button></div>

            <div className="capture-card">
              <label className="field"><span>Feature name</span><input value={form.feature_name} onChange={(e) => updateField("feature_name", e.target.value)} placeholder="e.g. AI Ticket Routing" /></label>
              <Field label="Natural-language feature description" rows={7} value={form.feature_description} onChange={(value) => updateField("feature_description", value)} placeholder="Describe actors, workflow, business rules, thresholds, and expected behavior." />
              <div className="form-grid">
                <Field label="Business objective" value={form.business_objective} onChange={(value) => updateField("business_objective", value)} placeholder="What measurable outcome should change?" />
                <Field label="Primary actor" value={form.primary_actor} onChange={(value) => updateField("primary_actor", value)} placeholder="Be specific: support agent, payment analyst, system scheduler..." />
                <Field label="Data inputs and outputs" value={form.data_inputs_outputs} onChange={(value) => updateField("data_inputs_outputs", value)} placeholder="What data arrives, changes, and leaves the workflow?" />
                <Field label="Downstream dependencies" value={form.downstream_dependencies} onChange={(value) => updateField("downstream_dependencies", value)} placeholder="Which services or teams are called, and what can fail?" />
                <Field label="Edge cases and error conditions" value={form.edge_cases} onChange={(value) => updateField("edge_cases", value)} placeholder="Invalid input, unavailable dependency, abandonment, timeout, duplicate request..." />
                <Field label="Compliance and governance" value={form.compliance_context} onChange={(value) => updateField("compliance_context", value)} placeholder="Audit, retention, consent, access, privacy, or industry constraints." />
              </div>
              <label className="field"><span>Domain prompt pack</span><select value={form.domain_pack} onChange={(e) => updateField("domain_pack", e.target.value as IntakeForm["domain_pack"])}><option value="generic">Generic product</option><option value="banking">Banking and payments</option><option value="support">Customer support automation</option><option value="compliance">Privacy and compliance</option></select><small>Domain packs add vocabulary and review rules. They do not assert compliance.</small></label>
            </div>
            <div className="capture-actions"><p>All generated content requires human review. Confidence flags identify missing context rather than hiding it.</p><button className="primary large" disabled={!canGenerate(form) || busy} onClick={generate}>{busy ? "Generating and validating…" : "Generate artifacts"}</button></div>
          </section>
        ) : selected ? (
          <>
            <div className="review-toolbar"><button onClick={() => setRun(null)}>← Edit intake</button>{selectedLatestRun && selectedLatestRun.id !== run.id && <button onClick={() => setRun(selectedLatestRun)}>Open latest run</button>}</div>
            <ArtifactReview session={selected} run={run} onRunChanged={(updated) => { setRun(updated); refreshSessions(selected.id).catch(() => undefined); }} />
          </>
        ) : null}
      </main>
    </div>
  );
}
