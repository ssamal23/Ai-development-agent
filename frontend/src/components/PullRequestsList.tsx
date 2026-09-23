import '../styles/PullRequestsList.css'

const pullRequests = [
  {
    id: '#421',
    ticket: 'AB-099',
    title: 'Update dealer activation flow',
    status: 'Merged',
    date: 'May 27, 2025',
    author: 'John Doe',
  },
  {
    id: '#420',
    ticket: 'AB-098',
    title: 'Add user role management',
    status: 'Merged',
    date: 'May 27, 2025',
    author: 'John Doe',
  },
  {
    id: '#419',
    ticket: 'AB-097',
    title: 'Fix stock calculation issue',
    status: 'Merged',
    date: 'May 26, 2025',
    author: 'John Doe',
  },
]

export default function PullRequestsList() {
  return (
    <div className="pr-list">
      {pullRequests.map((pr) => (
        <div key={pr.id} className="pr-item">
          <div className="pr-main">
            <a href="#" className="pr-id">{pr.id}</a>
            <div className="pr-details">
              <p className="pr-title">{pr.title}</p>
              <p className="pr-ticket">{pr.ticket}</p>
            </div>
          </div>
          <div className="pr-meta">
            <span className="pr-status merged">{pr.status}</span>
            <span className="pr-date">{pr.date}</span>
            <span className="pr-author">{pr.author}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
