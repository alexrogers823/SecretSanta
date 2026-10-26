import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { Header } from '../common'
import DashboardPrompt from '../components/DashboardPrompt'
import { useAuth } from '../context/AuthContext'
import useMatch, { MatchProvider } from './useMatch'

jest.mock('../api/client', () => ({
  ...jest.requireActual('../api/client'),
  apiFetch: jest.fn(),
}))
jest.mock('../context/AuthContext', () => ({ useAuth: jest.fn(), isAdmin: () => false }))
jest.mock('../context/AuthModalContext', () => ({ useAuthModal: () => ({ openLogin: jest.fn(), openSignup: jest.fn() }) }))

const USER = { id: 'u1', first_name: 'Ann' }

const MatchStatus = () => {
  const { match, error } = useMatch()
  return <div data-testid="match">{error || (match ? String(match.revealed) : 'loading')}</div>
}

const renderWithMatch = ui => render(<MemoryRouter><MatchProvider>{ui}</MatchProvider></MemoryRouter>)

beforeEach(() => {
  jest.clearAllMocks()
  jest.useFakeTimers()
  jest.setSystemTime(new Date('2026-11-25T16:59:00Z'))  // a minute before 12pm EST
  useAuth.mockReturnValue({ user: USER })
})

afterEach(() => jest.useRealTimers())

const flush = () => act(async () => { await Promise.resolve() })

test('does nothing while signed out', async () => {
  useAuth.mockReturnValue({ user: null })
  renderWithMatch(<MatchStatus />)
  await flush()
  expect(apiFetch).not.toHaveBeenCalled()
})

test('loads once and shares it with every component', async () => {
  apiFetch.mockResolvedValue({ revealed: true, receiver: { first_name: 'Bo' }, gifts: [] })
  renderWithMatch(<><MatchStatus /><DashboardPrompt user={USER} /></>)
  await flush()
  expect(apiFetch).toHaveBeenCalledTimes(1)
  expect(apiFetch).toHaveBeenCalledWith('/api/matches/me')
  expect(screen.getByTestId('match')).toHaveTextContent('true')
  expect(screen.getByText("It's here Ann! Check who your person is")).toBeInTheDocument()
})

test('fetches again once the reveal time passes', async () => {
  apiFetch
    .mockResolvedValueOnce({ revealed: false, reveal_at: '2026-11-25T17:00:00+00:00' })
    .mockResolvedValueOnce({ revealed: true, receiver: { first_name: 'Bo' }, gifts: [] })
  renderWithMatch(<MatchStatus />)
  await flush()
  expect(screen.getByTestId('match')).toHaveTextContent('false')

  await act(async () => { jest.advanceTimersByTime(59 * 1000) })
  expect(apiFetch).toHaveBeenCalledTimes(1)

  await act(async () => { jest.advanceTimersByTime(2 * 1000) })
  await flush()
  expect(apiFetch).toHaveBeenCalledTimes(2)
  expect(screen.getByTestId('match')).toHaveTextContent('true')
})

test('does not schedule reveals more than ~24 days away', async () => {
  apiFetch.mockResolvedValue({ revealed: false, reveal_at: '2027-11-25T17:00:00+00:00' })
  renderWithMatch(<MatchStatus />)
  await flush()
  await act(async () => { jest.advanceTimersByTime(60 * 1000) })
  expect(apiFetch).toHaveBeenCalledTimes(1)
})

test('clears the match when the user signs out', async () => {
  apiFetch.mockResolvedValue({ revealed: true, receiver: null, gifts: [] })
  const { rerender } = renderWithMatch(<MatchStatus />)
  await flush()
  expect(screen.getByTestId('match')).toHaveTextContent('true')

  useAuth.mockReturnValue({ user: null })
  rerender(<MemoryRouter><MatchProvider><MatchStatus /></MatchProvider></MemoryRouter>)
  await flush()
  expect(screen.getByTestId('match')).toHaveTextContent('loading')
})

test('reports errors', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  apiFetch.mockRejectedValue(new TypeError('Failed to fetch'))
  renderWithMatch(<MatchStatus />)
  await flush()
  expect(screen.getByTestId('match')).toHaveTextContent('Something went wrong')
})

test('home page card shows the pre-reveal message until the server says otherwise', async () => {
  apiFetch.mockResolvedValue({ revealed: false, reveal_at: '2027-11-25T17:00:00+00:00' })
  renderWithMatch(<DashboardPrompt user={USER} />)
  await flush()
  expect(screen.getByText(/add your information and gift requests/)).toBeInTheDocument()
})

// 2.13: the header countdown uses the server's reveal time

test('header counts down to the server reveal time when signed in', async () => {
  apiFetch.mockResolvedValue({ revealed: false, reveal_at: '2026-11-25T17:30:00+00:00' })
  renderWithMatch(<Header />)
  await flush()
  await act(async () => { jest.advanceTimersByTime(1000) })
  // 16:59:01 -> 17:30:00 is 30m 59s, not the 59s left until the default Nov 25th 12pm EST
  expect(screen.getByText(/Countdown to Your Match/).parentElement).toHaveTextContent('0d 00h 30m 59s')
})

test('header falls back to Nov 25th 12pm EST when signed out', async () => {
  useAuth.mockReturnValue({ user: null })
  renderWithMatch(<Header />)
  await flush()
  await act(async () => { jest.advanceTimersByTime(1000) })
  expect(screen.getByText(/Countdown to Your Match/).parentElement).toHaveTextContent('0d 00h 00m 59s')
})
