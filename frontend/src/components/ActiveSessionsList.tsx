import '../styles/ActiveSessionsList.css'

const sessions = [
  {
    id: 'AB-101',
    title: 'Add retailer filter to inventory',
    branch: 'ai/AB-101-retailer-filter',
    session: 'S-1001',
    stages: [
      { name: 'Plan', completed: true },
      { name: 'Code', completed: true },
      { name: 'Test', completed: false },
      { name: 'Build', completed: false },
      { name: 'PR', completed: false },
    ],
    status: 'Running Tests',
    updated: 'Updated 2 min ago',
  },
  {
    id: 'AB-102',
    title: 'Export invoice to Excel',
    branch: 'ai/AB-102-export-excel',
    session: 'S-1002',
    stages: [
      { name: 'Plan', completed: true },
      { name: 'Code', completed: true },
      { name: 'Test', completed: false },
      { name: 'Build', completed: false },
      { name: 'PR', completed: false },
    ],
    status: 'Coding',
    updated: 'Updated 5 min ago',
  },
  {
    id: 'AB-103',
    title: 'Add vehicle search',
    branch: 'ai/AB-103-vehicle-search',
    session: 'S-1003',
    stages: [
      { name: 'Plan', completed: true },
      { name: 'Code', completed: false },
      { name: 'Test', completed: false },
      { name: 'Build', completed: false },
      { name: 'PR', completed: false },
    ],
    status: 'Planning',
    updated: 'Updated 10 min ago',
  },
]

export default function ActiveSessionsList() {
  return (
    <div className="sessions-list">
      {sessions.map((session) => (
        <div key={session.id} className="session-item">
          <div className="session-header">
            <div className="session-info">
              <h4 className="session-title">{session.title}</h4>
              <p className="session-branch">{session.branch}</p>
            </div>
            <div className="session-status">
              <p className="status-label">{session.status}</p>
              <p className="status-time">{session.updated}</p>
            </div>
          </div>
          <div className="session-stages">
            {session.stages.map((stage) => (
              <div
                key={stage.name}
                className={`stage ${stage.completed ? 'completed' : ''}`}
                title={stage.name}
              >
                {stage.name.charAt(0)}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
