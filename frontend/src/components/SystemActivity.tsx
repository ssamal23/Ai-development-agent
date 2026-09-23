import '../styles/SystemActivity.css'

const activities = [
  {
    id: 1,
    message: 'Repository indexing completed',
    timestamp: 'May 28, 2025 09:45 AM',
    icon: '✓',
  },
  {
    id: 2,
    message: 'Azure DevOps connection healthy',
    timestamp: 'May 28, 2025 08:40 AM',
    icon: '✓',
  },
  {
    id: 3,
    message: 'GitHub connection healthy',
    timestamp: 'May 28, 2025 08:40 AM',
    icon: '✓',
  },
  {
    id: 4,
    message: 'Project onboarding completed',
    timestamp: 'May 28, 2025 09:35 AM',
    icon: '✓',
  },
]

export default function SystemActivity() {
  return (
    <div className="activity-list">
      {activities.map((activity) => (
        <div key={activity.id} className="activity-item">
          <div className="activity-icon">{activity.icon}</div>
          <div className="activity-content">
            <p className="activity-message">{activity.message}</p>
            <p className="activity-time">{activity.timestamp}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
