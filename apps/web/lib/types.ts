export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Connection {
  id: string;
  n8n_base_url: string;
  last_sync_status: string;
  last_sync_error: string | null;
  last_sync_at: string | null;
  created_at: string;
}

export type HealthStatus = "healthy" | "failing" | "silent" | "unused";

export interface Workflow {
  id: string;
  n8n_workflow_id: string;
  name: string;
  enabled: boolean;
  last_synced_at: string | null;
  health_status: HealthStatus;
  run_count_7d: number;
  error_count_7d: number;
  run_count_30d: number;
  error_count_30d: number;
  summary: string | null;
  summary_generated_at: string | null;
}

export interface SyncResult {
  workflows_synced: number;
  executions_synced: number;
  last_sync_status: string;
  last_sync_error: string | null;
  last_sync_at: string | null;
}

export interface WorkflowSummary {
  workflow_id: string;
  summary: string;
  generated_at: string;
}

export type AlertType = "failing" | "silent";

export interface Alert {
  id: string;
  workflow_id: string;
  workflow_name: string;
  alert_type: AlertType;
  triggered_at: string;
  resolved_at: string | null;
  email_sent_at: string | null;
  email_error: string | null;
}
