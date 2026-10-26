import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ApiError, apiFetch } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useAuthModal } from '../context/AuthModalContext'
import QuestionsSection from '../modules/Admin/QuestionsSection'
import QuestionsPrompt from './QuestionsPrompt'

jest.mock('../api/client', () => ({
  ...jest.requireActual('../api/client'),
  apiFetch: jest.fn(),
}))
jest.mock('../context/AuthContext', () => ({ useAuth: jest.fn() }))
jest.mock('../context/AuthModalContext', () => ({ useAuthModal: jest.fn() }))

const openLogin = jest.fn()

beforeEach(() => {
  jest.clearAllMocks()
  useAuth.mockReturnValue({ user: { id: 'u1', first_name: 'Ann' } })
  useAuthModal.mockReturnValue({ openLogin })
})

const askQuestion = text => {
  fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
  if (text !== undefined) fireEvent.change(document.getElementById('text'), { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: 'Submit Question' }))
}

// Asking (2.9)

test('signed-out visitors are asked to log in first', () => {
  useAuth.mockReturnValue({ user: null })
  render(<QuestionsPrompt />)
  fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
  expect(openLogin).toHaveBeenCalled()
  expect(screen.queryByText('Submit Question')).not.toBeInTheDocument()
})

test('sends only the question text, then closes and confirms', async () => {
  apiFetch.mockResolvedValue({ sent: true })
  render(<QuestionsPrompt />)
  askQuestion('Is there a price limit?')

  expect(await screen.findByText('Your question was sent anonymously.')).toBeInTheDocument()
  expect(apiFetch).toHaveBeenCalledWith('/api/questions', { method: 'POST', body: { text: 'Is there a price limit?' } })
  expect(screen.queryByRole('button', { name: 'Submit Question' })).not.toBeInTheDocument()
})

test('the form says the question is anonymous', () => {
  render(<QuestionsPrompt />)
  fireEvent.click(screen.getByRole('button', { name: 'Ask Question' }))
  expect(screen.getByText(/sent anonymously/)).toBeInTheDocument()
})

test('an empty question is not sent', async () => {
  render(<QuestionsPrompt />)
  askQuestion('   ')
  expect(await screen.findByText('Please write your question first.')).toBeInTheDocument()
  expect(apiFetch).not.toHaveBeenCalled()
})

test('a question over the server limit is not sent', async () => {
  render(<QuestionsPrompt />)
  askQuestion('x'.repeat(2001))
  expect(await screen.findByText('Questions can be up to 2000 characters.')).toBeInTheDocument()
  expect(apiFetch).not.toHaveBeenCalled()
})

test('server errors stay in the form', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  apiFetch.mockRejectedValue(new ApiError('sign in required', 401, { error: 'sign in required' }))
  render(<QuestionsPrompt />)
  askQuestion('Hello?')
  expect(await screen.findByText('sign in required')).toBeInTheDocument()
  expect(screen.queryByText('Your question was sent anonymously.')).not.toBeInTheDocument()
})

// Admin list (2.8)

test('admin sees question text and date, with no asker', async () => {
  apiFetch.mockResolvedValue([
    { id: 'q2', text: 'Second?', created_at: '2026-11-02T12:00:00+00:00', answered: false },
    { id: 'q1', text: 'First?', created_at: '2026-11-01T12:00:00+00:00', answered: false },
  ])
  render(<QuestionsSection />)
  expect(await screen.findByText('Second?')).toBeInTheDocument()
  expect(apiFetch).toHaveBeenCalledWith('/api/questions')
  expect(screen.getAllByRole('listitem').map(item => item.textContent)).toEqual([
    expect.stringMatching(/^Second\?Nov 2, 2026/),
    expect.stringMatching(/^First\?Nov 1, 2026/),
  ])
  expect(screen.queryByText(/@/)).not.toBeInTheDocument()
  expect(screen.queryByText(/UI preview/)).not.toBeInTheDocument()
})

test('admin list handles no questions and errors', async () => {
  apiFetch.mockResolvedValueOnce([])
  const { unmount } = render(<QuestionsSection />)
  expect(await screen.findByText('No questions yet.')).toBeInTheDocument()
  unmount()

  jest.spyOn(console, 'error').mockImplementation(() => {})
  apiFetch.mockRejectedValueOnce(new ApiError('admin only', 403, { error: 'admin only' }))
  render(<QuestionsSection />)
  await waitFor(() => expect(screen.getByText('admin only')).toBeInTheDocument())
})
