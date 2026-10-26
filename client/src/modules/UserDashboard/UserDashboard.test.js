import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ApiError, apiFetch } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import useMatch from '../../hooks/useMatch'
import UserDashboard from '.'

jest.mock('../../api/client', () => ({
  ...jest.requireActual('../../api/client'),
  apiFetch: jest.fn(),
}))
jest.mock('../../context/AuthContext', () => ({ useAuth: jest.fn(), isAdmin: () => false }))
jest.mock('../../hooks/useMatch', () => jest.fn())
jest.mock('../../components/PhotoGallery', () => () => <div data-testid="photo-gallery" />)

const USER = { id: 'u1', first_name: 'Ann', last_name: 'Lee', email: 'ann@example.com', address: '1 Elf Rd', profile_picture_url: null }
const updateUser = jest.fn()

beforeEach(() => {
  jest.clearAllMocks()
  useAuth.mockReturnValue({ user: USER, loading: false, updateUser })
  useMatch.mockReturnValue({ match: { revealed: false, reveal_at: '2026-11-25T17:00:00+00:00' }, error: '' })
  apiFetch.mockResolvedValue([])
})

const renderDashboard = async () => {
  render(
    <MemoryRouter initialEntries={['/dashboard/u1']}>
      <Routes>
        <Route path="/dashboard/:userId" element={<UserDashboard />} />
        <Route path="/" element={<div>home page</div>} />
      </Routes>
    </MemoryRouter>
  )
  await act(async () => {})
}

const card = title => screen.getByText(title).closest('.MuiPaper-root')

// Sign-in state

test('waits for the session to load instead of redirecting', async () => {
  useAuth.mockReturnValue({ user: null, loading: true, updateUser })
  await renderDashboard()
  expect(screen.queryByText('home page')).not.toBeInTheDocument()
  expect(screen.queryByText(/Welcome back/)).not.toBeInTheDocument()
})

test('signed-out visitors are sent home', async () => {
  useAuth.mockReturnValue({ user: null, loading: false, updateUser })
  await renderDashboard()
  expect(screen.getByText('home page')).toBeInTheDocument()
})

test('shows your information and the photo gallery', async () => {
  await renderDashboard()
  expect(screen.getByText('Welcome back, Ann!')).toBeInTheDocument()
  expect(within(card('Your Information')).getByText('1 Elf Rd')).toBeInTheDocument()
  expect(screen.getByTestId('photo-gallery')).toBeInTheDocument()
})

// Your gifts (2.2: /api/me/gifts)

test('loads your gifts from /api/me/gifts', async () => {
  apiFetch.mockResolvedValue([{ id: 0, name: 'Socks', url: 'https://shop.example/socks', notes: 'wool' }])
  await renderDashboard()
  expect(apiFetch).toHaveBeenCalledWith('/api/me/gifts')
  const gifts = card('Your Desired Gifts')
  expect(within(gifts).getByRole('link', { name: 'Socks' })).toHaveAttribute('href', 'https://shop.example/socks')
  expect(within(gifts).getByText('wool')).toBeInTheDocument()
})

test('saving gifts sends them to /api/me/gifts and shows the saved list', async () => {
  await renderDashboard()
  expect(screen.getByText(/you haven't added your desired gifts yet/)).toBeInTheDocument()

  apiFetch.mockResolvedValueOnce([{ id: 0, name: 'Mug', url: null, notes: null }])
  fireEvent.click(within(card('Your Desired Gifts')).getByRole('button', { name: 'Add' }))
  fireEvent.change(document.getElementById('firstOption'), { target: { value: 'Mug' } })
  fireEvent.click(screen.getByRole('button', { name: 'Submit' }))

  await waitFor(() => expect(within(card('Your Desired Gifts')).getByText('Mug')).toBeInTheDocument())
  expect(apiFetch).toHaveBeenLastCalledWith('/api/me/gifts', {
    method: 'PUT', body: { gifts: [{ name: 'Mug', url: '', notes: '' }] },
  })
})

test('a rejected gift list keeps the form open with the server message', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  await renderDashboard()
  const message = 'gift 1 link must start with http:// or https://'
  apiFetch.mockRejectedValueOnce(new ApiError(message, 400, { error: message }))
  fireEvent.click(within(card('Your Desired Gifts')).getByRole('button', { name: 'Add' }))
  fireEvent.change(document.getElementById('firstOption'), { target: { value: 'Bad' } })
  fireEvent.change(document.getElementById('firstOptionUrl'), { target: { value: 'javascript:alert(1)' } })
  fireEvent.click(screen.getByRole('button', { name: 'Submit' }))
  expect(await screen.findByText(message)).toBeInTheDocument()
})

// Your match (2.2/2.7: /api/matches/me through useMatch)

test('before the reveal, the match cards say when to come back', async () => {
  await renderDashboard()
  expect(within(card("Your Chosen LB's Information")).getByText(/Come back after November 25th/)).toBeInTheDocument()
})

test('while the match is loading, it says so', async () => {
  useMatch.mockReturnValue({ match: null, error: '' })
  await renderDashboard()
  expect(within(card("Your Chosen LB's Information")).getByText('Checking for your assignment...')).toBeInTheDocument()
})

test('after the reveal, shows your receiver and their gifts', async () => {
  useMatch.mockReturnValue({ match: {
    revealed: true,
    receiver: { first_name: 'Bo', last_name: 'Ray', address: '2 Sled St', profile_picture_url: null },
    gifts: [{ id: 0, name: 'Scarf', url: null, notes: 'red' }],
  }, error: '' })
  await renderDashboard()
  const receiver = card("Your Chosen LB's Information")
  expect(within(receiver).getByText('Bo Ray')).toBeInTheDocument()
  expect(within(receiver).getByText('2 Sled St')).toBeInTheDocument()
  expect(within(card('His Desired Gifts')).getByText('Scarf')).toBeInTheDocument()
})

test('after the reveal, a receiver with no gifts yet is named', async () => {
  useMatch.mockReturnValue({ match: { revealed: true, receiver: { first_name: 'Bo', last_name: 'Ray', address: 'x' }, gifts: [] }, error: '' })
  await renderDashboard()
  expect(within(card('His Desired Gifts')).getByText("Bo hasn't added their desired gifts yet")).toBeInTheDocument()
})

test('a receiver who left after the draw shows that matches are being updated', async () => {
  useMatch.mockReturnValue({ match: { revealed: true, receiver: null, gifts: [] }, error: '' })
  await renderDashboard()
  expect(within(card("Your Chosen LB's Information")).getByText('Your assignment is being updated. Check back soon.')).toBeInTheDocument()
})

test('a match loading error is shown', async () => {
  useMatch.mockReturnValue({ match: null, error: 'Something went wrong. Please try again.' })
  await renderDashboard()
  expect(within(card("Your Chosen LB's Information")).getByText('Something went wrong. Please try again.')).toBeInTheDocument()
})

test('the old 40-second counter and /generate call are gone', async () => {
  jest.useFakeTimers()
  await renderDashboard()
  await act(async () => { jest.advanceTimersByTime(60 * 1000) })
  expect(apiFetch.mock.calls.map(([path]) => path)).toEqual(['/api/me/gifts'])
  jest.useRealTimers()
})

// Editing your profile updates the signed-in user

test('a saved profile edit updates the signed-in user', async () => {
  await renderDashboard()
  apiFetch.mockResolvedValueOnce({ ...USER, address: '9 Pole Ln' })
  fireEvent.click(within(card('Your Information')).getByRole('button', { name: 'Edit' }))
  fireEvent.change(document.getElementById('address'), { target: { value: '9 Pole Ln' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(updateUser).toHaveBeenCalledWith({ ...USER, address: '9 Pole Ln' }))
})
