import { Fragment, useEffect, useRef, useState } from 'react'
import {
  startTicketRun,
  getTicketSession,
  type Ticket,
  type TicketsResponse,
  type TicketSession,
} from '../api'
import TokenUsagePanel from './TokenUsagePanel'
import '../styles/TicketsTable.css'

type TicketStatus = 'idle' | 'running' | 'done' | 'error'

const PROGRESS_POLL_INTERVAL_MS = 3000

function timeAgo(isoString: string): string {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 1000))
  if (seconds < 60) return 'Updated just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `Updated ${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  return `Updated ${hours}h ago`
}

interface TicketsTableProps {
  ticketsData: TicketsResponse | null
  loading: boolean
  loadError: string
}

export default function TicketsTable({ ticketsData, loading, loadError }: TicketsTableProps) {
  const [statusByTicket, setStatusByTicket] = useState<Record<string, TicketStatus>>({})
  const [messageByTicket, setMessageByTicket] = useState<Record<string, string>>({})
  const [prUrlByTicket, setPrUrlByTicket] = useState<Record<string, string>>({})
  const [expandedByTicket, setExpandedByTicket] = useState<Record<string, boolean>>({})
  const [sessionByTicket, setSessionByTicket] = useState<Record<string, TicketSession | null>>({})

  const tickets = ticketsData?.tickets ?? []

  // Poll only tickets with an AI run actually in progress. The
  // expand arrow is just a viewer for the last known state (one
  // fetch on click, in toggleExpanded below) — it must not, by
  // itself, start or extend continuous polling.
  const statusByTicketRef = useRef(statusByTicket)
  statusByTicketRef.current = statusByTicket

  useEffect(() => {
    const poll = async () => {
      const idsToPoll = tickets
        .map((t) => t.id)
        .filter((id) => statusByTicketRef.current[id] === 'running')

      for (const ticketId of idsToPoll) {
        try {
          const session = await getTicketSession(ticketId)
          setSessionByTicket((prev) => ({ ...prev, [ticketId]: session }))

          if (statusByTicketRef.current[ticketId] !== 'running') {
            continue
          }

          if (session?.done) {
            applySessionOutcome(ticketId, session)
          } else if (session === null) {
            // The backend has no record of this run (e.g. it
            // restarted mid-run). Without this, a ticket stuck
            // in 'running' with no matching session would poll
            // forever with no way to stop.
            setStatusByTicket((prev) => ({ ...prev, [ticketId]: 'error' }))
            setMessageByTicket((prev) => ({
              ...prev,
              [ticketId]: 'Lost track of this run (server may have restarted).',
            }))
          }
        } catch {
          // Transient poll failure — try again on the next tick.
        }
      }
    }

    const interval = setInterval(poll, PROGRESS_POLL_INTERVAL_MS)
    void poll()

    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickets.map((t) => t.id).join(',')])

  const applySessionOutcome = (ticketId: string, session: TicketSession) => {
    if (session.error) {
      setStatusByTicket((prev) => ({ ...prev, [ticketId]: 'error' }))
      setMessageByTicket((prev) => ({ ...prev, [ticketId]: session.error! }))
      return
    }

    const result = session.result

    let message: string
    let outcome: TicketStatus = 'done'

    if (result?.pull_request?.success && result?.pull_request?.url) {
      message = `PR #${result.pull_request.number} created`
    } else if (result?.test_result?.final_status === 'TESTS_ESCALATED') {
      message = 'Tests failed 3x — escalated for review'
      outcome = 'error'
    } else if (result?.test_result?.final_status === 'VERIFICATION_ESCALATED') {
      message = 'Verification failed 3x — escalated for review'
      outcome = 'error'
    } else if (result?.test_result?.success === false) {
      message = result?.test_result?.message || 'Tests did not pass'
      outcome = 'error'
    } else {
      message = result?.pull_request?.message || 'Completed, but no PR was created'
    }

    setStatusByTicket((prev) => ({ ...prev, [ticketId]: outcome }))
    setMessageByTicket((prev) => ({ ...prev, [ticketId]: message }))

    if (result?.pull_request?.url) {
      setPrUrlByTicket((prev) => ({ ...prev, [ticketId]: result.pull_request.url! }))
    }
  }

  const toggleExpanded = async (ticketId: string) => {
    const nextExpanded = !expandedByTicket[ticketId]
    setExpandedByTicket((prev) => ({ ...prev, [ticketId]: nextExpanded }))

    // Refetch every time a row is opened (not just the first
    // time ever) so a reopened row shows the current state
    // rather than whatever was cached from an earlier expand.
    if (nextExpanded) {
      try {
        const session = await getTicketSession(ticketId)
        setSessionByTicket((prev) => ({ ...prev, [ticketId]: session }))
      } catch {
        setSessionByTicket((prev) => ({ ...prev, [ticketId]: null }))
      }
    }
  }

  const getStateColor = (state: string) => {
    const stateColors: { [key: string]: string } = {
      'New': '#2196F3',
      'In Progress': '#FF9800',
      'To Do': '#9E9E9E',
      'Done': '#4CAF50',
    }
    return stateColors[state] || '#9E9E9E'
  }

  const getPriorityColor = (priority: string) => {
    const priorityColors: { [key: string]: string } = {
      'High': '#F44336',
      'Medium': '#FF9800',
      'Low': '#4CAF50',
    }
    return priorityColors[priority] || '#9E9E9E'
  }

  const handleStartAI = async (ticket: Ticket) => {
    setStatusByTicket((prev) => ({ ...prev, [ticket.id]: 'running' }))
    setMessageByTicket((prev) => ({ ...prev, [ticket.id]: '' }))
    setPrUrlByTicket((prev) => ({ ...prev, [ticket.id]: '' }))
    setSessionByTicket((prev) => ({ ...prev, [ticket.id]: null }))
    setExpandedByTicket((prev) => ({ ...prev, [ticket.id]: true }))

    try {
      // Kicks off the pipeline (plan, code, verify, test, PR)
      // on the server and returns immediately. The polling
      // effect above picks up progress and the final outcome.
      await startTicketRun(ticket)
    } catch (error) {
      setStatusByTicket((prev) => ({ ...prev, [ticket.id]: 'error' }))
      setMessageByTicket((prev) => ({
        ...prev,
        [ticket.id]: error instanceof Error ? error.message : 'Something went wrong',
      }))
    }
  }

  if (loading) {
    return <p className="table-footer">Loading tickets...</p>
  }

  if (loadError) {
    return <p className="table-footer">Could not load tickets: {loadError}</p>
  }

  return (
    <div className="tickets-table-container">
      {ticketsData && (
        <div className="tickets-summary-bar">
          <span className="summary-item">Sprint {ticketsData.sprint_no}</span>
          <span className="summary-item summary-done">
            {ticketsData.completed_tickets_count} completed
          </span>
          <span className="summary-item summary-in-progress">
            {ticketsData.in_progress_tickets_count} in progress
          </span>
        </div>
      )}

      <table className="tickets-table">
        <thead>
          <tr>
            <th className="expand-col"></th>
            <th>ID</th>
            <th>Title</th>
            <th>State</th>
            <th>Priority</th>
            <th>Assigned To</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => {
            const status = statusByTicket[ticket.id] ?? 'idle'
            const isDone = ticket.state === 'Done'
            const disabled = status === 'running' || isDone
            const isExpanded = expandedByTicket[ticket.id] ?? false
            const session = sessionByTicket[ticket.id]

            return (
              <Fragment key={ticket.id}>
                <tr>
                  <td className="expand-col">
                    <button
                      type="button"
                      className={`expand-toggle ${isExpanded ? 'expanded' : ''}`}
                      onClick={() => toggleExpanded(ticket.id)}
                      aria-label={isExpanded ? 'Collapse run details' : 'Expand run details'}
                      title="Show run progress"
                    >
                      ▾
                    </button>
                  </td>
                  <td className="ticket-id">{ticket.id}</td>
                  <td className="ticket-title">{ticket.title}</td>
                  <td>
                    <span
                      className="badge state-badge"
                      style={{ backgroundColor: getStateColor(ticket.state ?? '') }}
                    >
                      {ticket.state ?? 'Unknown'}
                    </span>
                  </td>
                  <td>
                    <span
                      className="badge priority-badge"
                      style={{ backgroundColor: getPriorityColor(ticket.priority ?? '') }}
                    >
                      {ticket.priority ?? 'Unknown'}
                    </span>
                  </td>
                  <td className="assignee">{ticket.assignee ?? 'Unassigned'}</td>
                  <td>
                    <button
                      className="action-button"
                      disabled={disabled}
                      title={isDone ? 'Ticket is already done' : undefined}
                      onClick={() => handleStartAI(ticket)}
                    >
                      {isDone
                        ? '✓ Done'
                        : status === 'running'
                        ? 'Running...'
                        : '▶ Start AI'}
                    </button>
                    {messageByTicket[ticket.id] && (
                      <p
                        className={
                          status === 'error' ? 'ticket-status-error' : 'ticket-status-ok'
                        }
                      >
                        {prUrlByTicket[ticket.id] ? (
                          <a
                            href={prUrlByTicket[ticket.id]}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {messageByTicket[ticket.id]}
                          </a>
                        ) : (
                          messageByTicket[ticket.id]
                        )}
                      </p>
                    )}
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="ticket-progress-row">
                    <td colSpan={7}>
                      {session === undefined && (
                        <p className="progress-empty">Loading run details...</p>
                      )}
                      {session === null && (
                        <p className="progress-empty">
                          No AI run yet for this ticket. Click ▶ Start AI to begin.
                        </p>
                      )}
                      {session && (
                        <div className="session-item">
                          <div className="session-header">
                            <div className="session-info">
                              <h4 className="session-title">{session.title}</h4>
                              {session.branch && (
                                <p className="session-branch">{session.branch}</p>
                              )}
                              <p className="session-branch">Session: {session.session_id}</p>
                            </div>
                            <div className="session-status">
                              <p className="status-label">{session.status_label}</p>
                              <p className="status-time">{timeAgo(session.updated_at)}</p>
                            </div>
                          </div>
                          <div className="session-stages">
                            {session.stages.map((stage) => (
                              <div
                                key={stage.name}
                                className={`stage stage-${stage.status}`}
                                title={`${stage.name}: ${stage.status}`}
                              >
                                {stage.status === 'running' ? (
                                  <span className="stage-spinner" />
                                ) : stage.status === 'done' ? (
                                  '✓'
                                ) : stage.status === 'error' ? (
                                  '✕'
                                ) : (
                                  stage.name.charAt(0)
                                )}
                              </div>
                            ))}
                          </div>
                          <TokenUsagePanel usage={session.token_usage} />
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
      <p className="table-footer">Showing {tickets.length} of {tickets.length} tickets</p>
    </div>
  )
}
