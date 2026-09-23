import StatCard from '../StatCard'
import TicketsTable from '../TicketsTable'
import ActiveSessionsList from '../ActiveSessionsList'
import PullRequestsList from '../PullRequestsList'
import SystemActivity from '../SystemActivity'
import SessionDetails from '../SessionDetails'
import '../../styles/DashboardView.css'

export default function DashboardView() {
  return (
    <div className="dashboard-view">
      <div className="dashboard-grid">
        {/* Top Stats Section */}
        <div className="stats-section">
          <StatCard
            title="My Tickets"
            value="8"
            subtitle="Assigned to me"
            action="View all tickets"
          />
          <StatCard
            title="Active Sessions"
            value="3"
            subtitle="In progress"
            action="View sessions"
          />
          <StatCard
            title="PRs Created"
            value="12"
            subtitle="This Sprint"
            action="View pull requests"
          />
          <StatCard
            title="Completed"
            value="5"
            subtitle="This Sprint"
            action="View completed"
          />
        </div>

        {/* Main Content Area */}
        <div className="content-area">
          <div className="content-left">
            {/* Tickets Table */}
            <div className="section-card">
              <h2 className="section-title">My Azure DevOps Tickets</h2>
              <TicketsTable />
            </div>

            {/* Active Sessions */}
            <div className="section-card">
              <div className="section-header">
                <h2 className="section-title">Active Sessions</h2>
                <a href="#" className="view-all-link">View all sessions →</a>
              </div>
              <ActiveSessionsList />
            </div>

            {/* Recent Pull Requests */}
            <div className="section-card">
              <div className="section-header">
                <h2 className="section-title">Recent Pull Requests</h2>
                <a href="#" className="view-all-link">View all PRs →</a>
              </div>
              <PullRequestsList />
            </div>
          </div>

          <div className="content-right">
            {/* Session Details */}
            <SessionDetails />

            {/* System Activity */}
            <div className="section-card">
              <div className="section-header">
                <h2 className="section-title">System Activity</h2>
                <a href="#" className="view-all-link">View all logs →</a>
              </div>
              <SystemActivity />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
