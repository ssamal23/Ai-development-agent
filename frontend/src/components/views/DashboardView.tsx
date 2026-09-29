import { useEffect, useState } from 'react'
import StatCard from '../StatCard'
import TicketsTable from '../TicketsTable'
import ActiveSessionsList from '../ActiveSessionsList'
import PullRequestsList from '../PullRequestsList'
import SystemActivity from '../SystemActivity'
import SessionDetails from '../SessionDetails'
import { fetchTickets, type TicketsResponse } from '../../api'
import '../../styles/DashboardView.css'

export default function DashboardView() {
  const [ticketsData, setTicketsData] = useState<TicketsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    fetchTickets()
      .then(setTicketsData)
      .catch((error: Error) => setLoadError(error.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="dashboard-view">
      <div className="dashboard-grid">
        {/* Top Stats Section */}
        <div className="stats-section">
          <StatCard
            title="My Tickets"
            value={ticketsData ? String(ticketsData.total_tickets) : '-'}
            subtitle="In the backlog"
            action=""
          />
          <StatCard
            title="Active Sessions"
            value= {ticketsData ? `${ticketsData.in_progress_tickets_count}` : '-'}
            subtitle="In progress"
            action=""
          />
          <StatCard
            title="Current Sprint"
            value={ticketsData ? `Sprint ${ticketsData.sprint_no}` : '-'}
            subtitle={
              ticketsData ? `${ticketsData.in_progress_tickets_count} in progress` : ''
            }
            action=""
          />
          <StatCard
            title="Completed"
            value={ticketsData ? String(ticketsData.completed_tickets_count) : '-'}
            subtitle="This Sprint"
            action=""
          />
        </div>

        {/* Main Content Area */}
        <div className="content-area">
          <div className="content-left">
            {/* Tickets Table */}
            <div className="section-card">
              <h2 className="section-title">My Azure DevOps Tickets</h2>
              <TicketsTable
                ticketsData={ticketsData}
                loading={loading}
                loadError={loadError}
              />
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
