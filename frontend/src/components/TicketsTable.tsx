import '../styles/TicketsTable.css'

const tickets = [
  {
    id: 'AB-101',
    title: 'Add retailer filter to inventory',
    state: 'New',
    priority: 'High',
    assignee: 'John Doe',
  },
  {
    id: 'AB-102',
    title: 'Export invoice to Excel',
    state: 'New',
    priority: 'Medium',
    assignee: 'John Doe',
  },
  {
    id: 'AB-103',
    title: 'Add vehicle search',
    state: 'In Progress',
    priority: 'Medium',
    assignee: 'John Doe',
  },
  {
    id: 'AB-104',
    title: 'Fix invoice calculation',
    state: 'New',
    priority: 'High',
    assignee: 'John Doe',
  },
  {
    id: 'AB-105',
    title: 'Add allocation validation',
    state: 'To Do',
    priority: 'Low',
    assignee: 'John Doe',
  },
]

export default function TicketsTable() {
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

  return (
    <div className="tickets-table-container">
      <table className="tickets-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>State</th>
            <th>Priority</th>
            <th>Assigned To</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr key={ticket.id}>
              <td className="ticket-id">{ticket.id}</td>
              <td className="ticket-title">{ticket.title}</td>
              <td>
                <span
                  className="badge state-badge"
                  style={{ backgroundColor: getStateColor(ticket.state) }}
                >
                  {ticket.state}
                </span>
              </td>
              <td>
                <span
                  className="badge priority-badge"
                  style={{ backgroundColor: getPriorityColor(ticket.priority) }}
                >
                  {ticket.priority}
                </span>
              </td>
              <td className="assignee">{ticket.assignee}</td>
              <td>
                <button className="action-button">▶ Start AI</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="table-footer">Showing 5 of 8 tickets</p>
    </div>
  )
}
