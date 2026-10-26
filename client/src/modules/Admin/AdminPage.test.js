import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ApiError, apiFetch } from '../../api/client'
import { useAuth } from '../../context/AuthContext'
import AdminPage from '.'

jest.mock('../../api/client', () => ({
  ...jest.requireActual('../../api/client'),
  apiFetch: jest.fn(),
}))
jest.mock('../../context/AuthContext', () => ({
  useAuth: jest.fn(),
  isAdmin: user => user?.is_admin === true,
}))
// The questions list has its own tests (questions.test.js)
jest.mock('./QuestionsSection', () => () => null)

const ADMIN = { id: 'admin', first_name: 'Ad', last_name: 'Min', email: 'admin@example.com', is_admin: true }
const OVERVIEW = {
  season: 2026,
  generation: 1,
  users: [
    { id: 'admin', first_name: 'Ad', last_name: 'Min', email: 'admin@example.com', address: '1 Rd', gifts: [], assigned_to: null, photo_count: 0 },
    { id: 'ann', first_name: 'Ann', last_name: 'Lee', email: 'ann@example.com', address: '2 Rd',
      gifts: [{ id: 0, name: 'Socks' }, { id: 1, name: 'Mug' }], assigned_to: { id: 'bo', first_name: 'Bo', last_name: 'Ray' }, photo_count: 3 },
    { id: 'bo', first_name: 'Bo', last_name: 'Ray', email: 'bo@example.com', address: '3 Rd', gifts: [], assigned_to: null, photo_count: 0 },
  ],
}

beforeEach(() => {
  jest.clearAllMocks()
  useAuth.mockReturnValue({ user: ADMIN, loading: false })
  apiFetch.mockImplementation(async path => {
    if (path === '/api/admin/overview') return OVERVIEW
    throw new Error(`unexpected ${path}`)
  })
})

const renderAdmin = async () => {
  render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/" element={<div>home page</div>} />
      </Routes>
    </MemoryRouter>
  )
  await act(async () => {})
}

const row = name => screen.getByText(name).closest('tr')

test('non-admins are sent home without loading anything', async () => {
  useAuth.mockReturnValue({ user: { ...ADMIN, is_admin: false }, loading: false })
  await renderAdmin()
  expect(screen.getByText('home page')).toBeInTheDocument()
  expect(apiFetch).not.toHaveBeenCalled()
})

test('waits for the session before deciding', async () => {
  useAuth.mockReturnValue({ user: null, loading: true })
  await renderAdmin()
  expect(screen.queryByText('home page')).not.toBeInTheDocument()
})

test('loads everything from one overview call', async () => {
  await renderAdmin()
  expect(apiFetch.mock.calls.map(([path]) => path)).toEqual(['/api/admin/overview'])
  expect(within(row('Ann Lee')).getByText('Socks, Mug')).toBeInTheDocument()
  expect(within(row('Bo Ray')).getByText('No gifts yet')).toBeInTheDocument()
  expect(within(row('Bo Ray')).getByText('Not generated')).toBeInTheDocument()
})

test('a match is hidden until the admin reveals it', async () => {
  await renderAdmin()
  const annRow = row('Ann Lee')
  fireEvent.click(within(annRow).getByRole('button', { name: 'Reveal' }))
  expect(within(annRow).getByRole('button', { name: 'Bo Ray' })).toBeInTheDocument()
})

test("the admin can't delete their own account", async () => {
  await renderAdmin()
  expect(within(row('Ad Min')).getByRole('button', { name: 'Delete' })).toBeDisabled()
})

test('deleting a user removes them and shows the regenerate warning', async () => {
  await renderAdmin()
  const warning = 'Matches were already drawn for this season. Regenerate them so everyone has a match.'
  apiFetch.mockResolvedValueOnce({ deleted: 'bo', warning })
  fireEvent.click(within(row('Bo Ray')).getByRole('button', { name: 'Delete' }))
  fireEvent.click(screen.getAllByRole('button', { name: 'Delete' }).at(-1))  // confirm in the dialog

  await waitFor(() => expect(screen.queryByText('Bo Ray')).not.toBeInTheDocument())
  expect(apiFetch).toHaveBeenLastCalledWith('/api/users/bo', { method: 'DELETE' })
  expect(screen.getByText(warning)).toBeInTheDocument()
})

test('regenerating updates every match and clears the warning', async () => {
  await renderAdmin()
  apiFetch.mockResolvedValueOnce({ deleted: 'x', warning: 'Regenerate them' })
  fireEvent.click(within(row('Bo Ray')).getByRole('button', { name: 'Delete' }))
  fireEvent.click(screen.getAllByRole('button', { name: 'Delete' }).at(-1))
  await screen.findByText('Regenerate them')

  apiFetch.mockResolvedValueOnce([
    { user_id: 'admin', assigned_to: { id: 'ann', first_name: 'Ann', last_name: 'Lee' } },
    { user_id: 'ann', assigned_to: { id: 'admin', first_name: 'Ad', last_name: 'Min' } },
  ])
  // findByRole waits until the delete dialog has finished closing and the page is interactive again
  fireEvent.click(await screen.findByRole('button', { name: 'Regenerate Matches' }))
  fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }))

  await waitFor(() => expect(within(row('Ad Min')).getByRole('button', { name: 'Reveal' })).toBeInTheDocument())
  expect(apiFetch).toHaveBeenLastCalledWith('/api/matches/regenerate', { method: 'POST' })
  expect(screen.queryByText('Regenerate them')).not.toBeInTheDocument()
})

test('a refused regenerate (e.g. only repeats are possible) shows the server reason', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  await renderAdmin()
  const reason = 'every possible draw repeats a pair from last year.'
  apiFetch.mockRejectedValueOnce(new ApiError(reason, 409, { error: reason }))
  fireEvent.click(screen.getByRole('button', { name: 'Regenerate Matches' }))
  fireEvent.click(screen.getByRole('button', { name: 'Regenerate' }))
  expect(await screen.findByText(reason)).toBeInTheDocument()
})

test('editing a user saves through the admin user route', async () => {
  await renderAdmin()
  apiFetch.mockResolvedValueOnce({ ...OVERVIEW.users[1], address: '9 Pole Ln' })
  fireEvent.click(within(row('Ann Lee')).getByRole('button', { name: 'Edit' }))
  fireEvent.change(document.getElementById('address'), { target: { value: '9 Pole Ln' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  await waitFor(() => expect(within(row('Ann Lee')).getByText('9 Pole Ln')).toBeInTheDocument())
  expect(apiFetch).toHaveBeenLastCalledWith('/api/users/ann', {
    method: 'PATCH', body: { first_name: 'Ann', last_name: 'Lee', email: 'ann@example.com', address: '9 Pole Ln' },
  })
  // The edit keeps the overview-only fields (gifts, match)
  expect(within(row('Ann Lee')).getByText('Socks, Mug')).toBeInTheDocument()
})

test('editing a user shows the server error, e.g. a duplicate email', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  await renderAdmin()
  const duplicate = 'a user with that email already exists'
  apiFetch.mockRejectedValueOnce(new ApiError(duplicate, 409, { error: duplicate }))
  fireEvent.click(within(row('Ann Lee')).getByRole('button', { name: 'Edit' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByText(duplicate)).toBeInTheDocument()
})
