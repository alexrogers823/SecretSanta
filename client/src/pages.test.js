import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { apiFetch } from './api/client'
import { Header, Modal } from './common'
import { useAuth } from './context/AuthContext'
import { useAuthModal } from './context/AuthModalContext'
import useMatch from './hooks/useMatch'
import About from './modules/About'
import Main from './modules/Main'
import { getNextChristmasDate, getNextMatchDate } from './utils/dateHelpers'
import * as dateHelpers from './utils/dateHelpers'

jest.mock('./api/client', () => ({
  ...jest.requireActual('./api/client'),
  apiFetch: jest.fn(),
}))
jest.mock('./context/AuthContext', () => ({
  useAuth: jest.fn(),
  isAdmin: user => user?.is_admin === true,
}))
jest.mock('./context/AuthModalContext', () => ({ useAuthModal: jest.fn() }))
jest.mock('./hooks/useMatch', () => jest.fn())
jest.mock('./components/PhotoGallery', () => () => <div data-testid="photo-gallery" />)
jest.mock('./components/PhotoUpload', () => () => <div data-testid="photo-upload" />)

const USER = { id: 'u1', first_name: 'Ann', last_name: 'Lee', is_admin: false }
const openLogin = jest.fn()
const openSignup = jest.fn()
const logout = jest.fn()

beforeEach(() => {
  jest.clearAllMocks()
  useAuth.mockReturnValue({ user: null, logout })
  useAuthModal.mockReturnValue({ openLogin, openSignup })
  useMatch.mockReturnValue({ match: null, error: '' })
})

const renderAt = (ui, path = '/') => render(
  <MemoryRouter initialEntries={[path]}>
    {ui}
    <Routes>
      <Route path="*" element={null} />
      <Route path="/admin" element={<div>admin page</div>} />
      <Route path="/dashboard/:id" element={<div>dashboard page</div>} />
    </Routes>
  </MemoryRouter>
)

// About (2.2)

test('About shows the text from /api/about', async () => {
  apiFetch.mockResolvedValue('Add your wish list before November 25th.')
  render(<About />)
  expect(await screen.findByText('Add your wish list before November 25th.')).toBeInTheDocument()
  expect(apiFetch).toHaveBeenCalledWith('/api/about')
})

// Home page (2.2, 2.16)

test('signed-out home page shows log-in cards and the public gallery, not uploads', async () => {
  render(<MemoryRouter><Main /></MemoryRouter>)
  await act(async () => {})
  expect(screen.getByTestId('photo-gallery')).toBeInTheDocument()
  expect(screen.queryByTestId('photo-upload')).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Log In' }))
  fireEvent.click(screen.getByRole('button', { name: 'Sign Up' }))
  expect(openLogin).toHaveBeenCalled()
  expect(openSignup).toHaveBeenCalled()
  // The old unused /api request is gone
  expect(apiFetch).not.toHaveBeenCalled()
})

test('signed-in home page shows photo upload and the dashboard card instead', async () => {
  useAuth.mockReturnValue({ user: USER, logout })
  render(<MemoryRouter><Main /></MemoryRouter>)
  await act(async () => {})
  expect(screen.getByTestId('photo-upload')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Go to Dashboard' })).toBeInTheDocument()
  expect(screen.queryByTestId('photo-gallery')).not.toBeInTheDocument()  // it's on the dashboard
})

// Header (2.5)

test('header shows Log In / Sign Up when signed out', () => {
  renderAt(<Header />)
  fireEvent.click(screen.getByRole('button', { name: 'Log In' }))
  expect(openLogin).toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: 'Log Out' })).not.toBeInTheDocument()
})

test('header menu shows the admin page only for admins (server flag)', () => {
  useAuth.mockReturnValue({ user: USER, logout })
  const { unmount } = renderAt(<Header />)
  fireEvent.click(screen.getByTestId('MenuIcon').closest('button'))
  expect(screen.queryByText('Admin Page')).not.toBeInTheDocument()
  unmount()

  useAuth.mockReturnValue({ user: { ...USER, is_admin: true }, logout })
  renderAt(<Header />)
  fireEvent.click(screen.getByTestId('MenuIcon').closest('button'))
  fireEvent.click(screen.getByText('Admin Page'))
  expect(screen.getByText('admin page')).toBeInTheDocument()
})

test('logging out signs out of Firebase and goes home', () => {
  useAuth.mockReturnValue({ user: USER, logout })
  renderAt(<Header />, '/dashboard/u1')
  fireEvent.click(screen.getByRole('button', { name: 'Log Out' }))
  expect(logout).toHaveBeenCalled()
  expect(screen.queryByText('dashboard page')).not.toBeInTheDocument()
})

// dateHelpers after 2.13

test('dateHelpers keeps only the display countdown helpers', () => {
  expect(Object.keys(dateHelpers).sort()).toEqual(['getNextChristmasDate', 'getNextMatchDate'])
})

test('countdown dates roll over to next year once passed', () => {
  jest.useFakeTimers()
  jest.setSystemTime(new Date('2026-11-25T16:59:59Z'))
  expect(getNextMatchDate().toISOString()).toBe('2026-11-25T17:00:00.000Z')  // 12pm EST
  jest.setSystemTime(new Date('2026-11-25T17:00:00Z'))
  expect(getNextMatchDate().toISOString()).toBe('2027-11-25T17:00:00.000Z')
  jest.setSystemTime(new Date('2026-12-26T00:00:00Z'))
  expect(getNextChristmasDate().toISOString()).toBe('2027-12-25T05:00:00.000Z')  // midnight EST
  jest.useRealTimers()
})

// Modal (2.6)

test('Modal wraps its content so MUI can move focus into it', () => {
  const Form = () => <form aria-label="inner form"><input aria-label="field" /></form>
  render(<Modal open handleCloseModal={() => {}}><Form /></Modal>)
  const form = screen.getByRole('form', { name: 'inner form' })
  expect(form.parentElement.tagName).toBe('DIV')
  expect(form.parentElement).toHaveAttribute('tabindex', '-1')
})
