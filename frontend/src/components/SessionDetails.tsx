import '../styles/SessionDetails.css'

export default function SessionDetails() {
  const sessionDetails = {
    id: 'AB-101',
    title: 'Add retailer filter to inventory',
    branch: 'ai/AB-101-retailer-filter',
    session: 'S-1001',
    status: 'Running Tests',
    startedAt: 'May 28, 2025 10:15 AM',
    estimatedCompletion: '10 mins',
    agent: 'GPT-4o',
    progress: [
      { stage: 'Ticket retrieved from Azure DevOps', time: '10:15 AM' },
      { stage: 'Requirement analyzed', time: '10:15 AM' },
      { stage: 'Repository analyzed', time: '10:16 AM' },
      { stage: 'Implementation plan created', time: '10:17 AM' },
      { stage: 'Plan approved by developer', time: '10:18 AM' },
      { stage: 'Code generation', time: '10:19 AM' },
      { stage: 'Running unit tests', time: '10:24 AM' },
      { stage: 'Build & validation', text: 'In Progress' },
      { stage: 'Create Pull Request', text: 'Pending' },
    ],
  }

  return (
    <div className="session-details-card">
      <div className="session-details-header">
        <h3 className="session-details-title">{sessionDetails.title}</h3>
        <span className="session-status-badge">Live</span>
      </div>

      <div className="session-details-info">
        <div className="info-row">
          <label>Session ID:</label>
          <span>{sessionDetails.session}</span>
        </div>
        <div className="info-row">
          <label>Branch:</label>
          <span className="branch-name">{sessionDetails.branch}</span>
        </div>
        <div className="info-row">
          <label>Started At:</label>
          <span>{sessionDetails.startedAt}</span>
        </div>
        <div className="info-row">
          <label>Estimated Completion:</label>
          <span>{sessionDetails.estimatedCompletion}</span>
        </div>
        <div className="info-row">
          <label>Agent:</label>
          <span>{sessionDetails.agent}</span>
        </div>
      </div>

      <div className="session-progress">
        <h4 className="progress-title">Progress</h4>
        <div className="progress-timeline">
          {sessionDetails.progress.map((item, index) => (
            <div key={index} className="progress-item">
              <div className="progress-marker"></div>
              <div className="progress-content">
                <p className="progress-stage">{item.stage}</p>
                <p className="progress-time">{item.time || item.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="session-actions">
        <button className="action-btn primary">▶ Open in IDE / Workspace</button>
      </div>
    </div>
  )
}
