const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface Ticket {
  id: string
  title: string
  description: string
  acceptance_criteria: string[]
  state?: string
  priority?: string
  assignee?: string
  /** A Figma frame link ("Copy link to selection") or a plain web page URL to match. */
  design_reference?: string
  /** A directly pasted/uploaded design image: a data URL (data:image/png;base64,...) or bare base64. */
  design_reference_image?: string
}

export type BoardProvider = 'none' | 'azure_boards' | 'jira' | 'github_issues'

export interface ProjectConfig {
  gitRepoUrl: string
  baseBranch: string
  gitToken: string
  boardProvider: BoardProvider
  boardOrgOrUrl: string
  boardProjectKey: string
  boardToken: string
}

const PROJECT_CONFIG_KEY = 'projectConfig'

export function loadProjectConfig(): ProjectConfig | null {
  try {
    const stored = localStorage.getItem(PROJECT_CONFIG_KEY)
    if (!stored) return null
    const parsed = JSON.parse(stored)
    return parsed?.gitRepoUrl ? parsed : null
  } catch {
    return null
  }
}

export function saveProjectConfig(config: ProjectConfig): void {
  localStorage.setItem(PROJECT_CONFIG_KEY, JSON.stringify(config))
}

export interface GitRepoInfo {
  owner: string
  repo: string
}

/**
 * Parse "owner/repo" out of a GitHub URL for display
 * purposes (project dropdown, header). Mirrors the
 * backend's RepositoryProvisionService._parse_owner_repo.
 */
export function parseGitRepoUrl(url: string): GitRepoInfo | null {
  const match = url.match(/github\.com[:/]+([^/]+)\/([^/.]+?)(?:\.git)?\/?$/i)
  if (!match) return null
  return { owner: match[1], repo: match[2] }
}

/**
 * Resolve which URL to fetch tickets from.
 *
 * When a board provider is configured with a URL, that URL
 * IS the ticket source (there's no real Azure Boards/Jira
 * integration yet — the configured URL is expected to
 * return the same `{ tickets: [...] }` shape our own mock
 * /api/tickets endpoint does). Falls back to that mock
 * endpoint when no board is configured.
 */
function resolveTicketsUrl(config: ProjectConfig | null): string {
  if (
    config?.boardProvider &&
    config.boardProvider !== 'none' &&
    config.boardOrgOrUrl.trim()
  ) {
    return config.boardOrgOrUrl.trim()
  }

  return `${API_BASE_URL}/api/tickets`
}

export interface TicketsResponse {
  total_tickets: number
  completed_tickets_count: number
  in_progress_tickets_count: number
  sprint_no: number
  tickets: Ticket[]
}

export async function fetchTickets(): Promise<TicketsResponse> {
  const projectConfig = loadProjectConfig()

  const url = resolveTicketsUrl(projectConfig)

  const headers: Record<string, string> = {}

  if (url !== `${API_BASE_URL}/api/tickets` && projectConfig?.boardToken) {
    headers['Authorization'] = `Bearer ${projectConfig.boardToken}`
  }

  const response = await fetch(url, { headers })

  if (!response.ok) {
    throw new Error(`Failed to load tickets from ${url} (${response.status})`)
  }

  return response.json()
}

export interface AnalyzeTicketResult {
  ticket: Ticket
  repo_config: Record<string, unknown>
  ticket_category: Record<string, unknown>
  analysis: string
  verification_result: Record<string, unknown>
  test_result: {
    success?: boolean
    final_status?: string
    message?: string
  }
  git_result: Record<string, unknown>
  pull_request: {
    success?: boolean
    url?: string
    number?: number
    message?: string
  }
}

export interface StartTicketRunResponse {
  session_id: string
  ticket_id: string
  status: string
}

/**
 * Kick off the ticket workflow. Returns immediately with a
 * session id — the workflow (plan, code, verify, test, PR)
 * runs in the background on the server. Poll
 * `getTicketSession` for live progress and the final result.
 */
export async function startTicketRun(ticket: Ticket): Promise<StartTicketRunResponse> {
  const projectConfig = loadProjectConfig()

  const response = await fetch(`${API_BASE_URL}/api/agent/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ticket,
      repository_url: projectConfig?.gitRepoUrl || null,
      branch: projectConfig?.baseBranch || null,
    }),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Starting the AI run failed (${response.status}): ${text}`)
  }

  return response.json()
}

export type StageStatus = 'pending' | 'running' | 'done' | 'error'

export interface TicketSessionStage {
  name: string
  status: StageStatus
}

export interface TokenUsageStage {
  name: string
  input_tokens: number
  output_tokens: number
  calls: number
}

export interface TokenUsageStep {
  node: string
  label: string
  stage: string | null
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  calls: number
  models: string[]
}

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  calls: number
  models: string[]
  stages: TokenUsageStage[]
  steps: TokenUsageStep[]
}

export interface TicketSession {
  session_id: string
  ticket_id: string
  title: string
  branch: string | null
  status_label: string
  stages: TicketSessionStage[]
  updated_at: string
  done: boolean
  error: string | null
  result: AnalyzeTicketResult | null
  token_usage?: TokenUsage
}

/**
 * Poll the live/last-known progress for a ticket's run.
 * Returns null when no run has ever been started for it
 * (backend responds 404 in that case).
 */
export async function getTicketSession(ticketId: string): Promise<TicketSession | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/agent/sessions/${encodeURIComponent(ticketId)}`,
  )

  if (response.status === 404) {
    return null
  }

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Failed to load run status (${response.status}): ${text}`)
  }

  return response.json()
}
