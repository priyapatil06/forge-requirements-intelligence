# Architecture

## Product stages

### 1. Capture

The frontend gathers a free-text feature description plus six explicit context fields. Those fields are persisted before generation so requirements provenance is not lost.

### 2. Structure

The backend combines the intake, selected domain pack, output schema, and safety constraints into one prompt. The LLM output is validated against Pydantic models. Invalid output is rejected or repaired once; it is never stored as a successful run without validation.

### 3. Deliver

A validated run can be reviewed, edited, approved, exported, or synchronized to Jira. Review actions are stored as an audit log.

## Data model

- `forge_sessions`: the intake and selected prompt pack
- `artifact_runs`: validated artifact JSON, model metadata, latency, status
- `review_actions`: approve/reject/comment events
- `jira_connections`: encrypted OAuth tokens and site metadata
- `jira_oauth_states`: short-lived CSRF state values

## Trust boundaries

- Claude and Jira credentials stay in the backend.
- The browser never receives API secrets.
- LLM output is treated as untrusted input and validated.
- Jira issue creation is user-initiated and project-specific.
- Confidence flags are mandatory output, not decorative metadata.

## Known architectural limitation

The sample application is single-workspace. It does not yet include user authentication or tenant isolation. Do not deploy it for multiple organizations without adding those controls.
