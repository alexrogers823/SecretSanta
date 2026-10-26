import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ApiError, apiFetch } from '../api/client'
import { useAuth } from '../context/AuthContext'
import PhotoGallery from './PhotoGallery'

jest.mock('../api/client', () => ({
  ...jest.requireActual('../api/client'),
  apiFetch: jest.fn(),
}))
jest.mock('../context/AuthContext', () => ({ useAuth: jest.fn() }))

const publicPhoto = id => ({ id, thumb_url: `https://x/thumbs/${id}`, display_url: `https://x/display/${id}`, created_at: '2026-12-01T12:00:00+00:00' })

beforeEach(() => {
  jest.clearAllMocks()
  useAuth.mockReturnValue({ user: null })
})

test('visitors see thumbnails without names or delete buttons', async () => {
  apiFetch.mockResolvedValue({ season: 2026, seasons: [2026], photos: [publicPhoto('a'), publicPhoto('b')] })
  render(<PhotoGallery />)
  const images = await screen.findAllByRole('img')
  expect(apiFetch).toHaveBeenCalledWith('/api/photos')
  expect(images.map(image => image.getAttribute('src'))).toEqual(['https://x/thumbs/a', 'https://x/thumbs/b'])
  expect(images[0]).toHaveAttribute('alt', 'Christmas photo')
  expect(screen.queryByLabelText('Delete photo')).not.toBeInTheDocument()
  expect(screen.queryByLabelText('Season')).not.toBeInTheDocument()  // only one season
})

test('clicking a thumbnail opens the full-size copy', async () => {
  apiFetch.mockResolvedValue({ season: 2026, seasons: [2026], photos: [publicPhoto('a')] })
  render(<PhotoGallery />)
  fireEvent.click(await screen.findByRole('img'))
  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByRole('img')).toHaveAttribute('src', 'https://x/display/a')
})

test('members see who posted, and delete only what they may', async () => {
  useAuth.mockReturnValue({ user: { id: 'u1' } })
  apiFetch.mockResolvedValueOnce({ season: 2026, seasons: [2026], photos: [
    { ...publicPhoto('mine'), owner_first_name: 'Ann', can_delete: true },
    { ...publicPhoto('theirs'), owner_first_name: 'Bo', can_delete: false },
  ] })
  render(<PhotoGallery />)
  expect(await screen.findByText('Bo')).toBeInTheDocument()
  expect(screen.getByAltText('Christmas photo from Ann')).toBeInTheDocument()
  expect(screen.getAllByLabelText('Delete photo')).toHaveLength(1)

  apiFetch.mockResolvedValueOnce(null)
  fireEvent.click(screen.getByLabelText('Delete photo'))
  fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Delete' }))

  await waitFor(() => expect(screen.queryByAltText('Christmas photo from Ann')).not.toBeInTheDocument())
  expect(apiFetch).toHaveBeenLastCalledWith('/api/photos/mine', { method: 'DELETE' })
  expect(screen.getByAltText('Christmas photo from Bo')).toBeInTheDocument()
})

test('a failed delete keeps the photo and shows why', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  useAuth.mockReturnValue({ user: { id: 'u1' } })
  apiFetch.mockResolvedValueOnce({ season: 2026, seasons: [2026], photos: [{ ...publicPhoto('mine'), owner_first_name: 'Ann', can_delete: true }] })
  render(<PhotoGallery />)
  fireEvent.click(await screen.findByLabelText('Delete photo'))

  apiFetch.mockRejectedValueOnce(new ApiError('Forbidden', 403, { error: 'Forbidden' }))
  fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Delete' }))
  expect(await screen.findByText('Forbidden')).toBeInTheDocument()
  expect(screen.getByAltText('Christmas photo from Ann')).toBeInTheDocument()
})

test('the season picker loads past seasons', async () => {
  apiFetch
    .mockResolvedValueOnce({ season: 2026, seasons: [2026, 2025], photos: [] })
    .mockResolvedValueOnce({ season: 2025, seasons: [2026, 2025], photos: [publicPhoto('old')] })
  render(<PhotoGallery />)
  expect(await screen.findByText('No photos from 2026 yet.')).toBeInTheDocument()

  fireEvent.mouseDown(screen.getByLabelText('Season'))
  fireEvent.click(await screen.findByRole('option', { name: '2025' }))
  expect(await screen.findByRole('img')).toHaveAttribute('src', 'https://x/thumbs/old')
  expect(apiFetch).toHaveBeenLastCalledWith('/api/photos?season=2025')
})

test('shows an error if photos cannot load', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  apiFetch.mockRejectedValue(new TypeError('Failed to fetch'))
  render(<PhotoGallery />)
  expect(await screen.findByText('Unable to load photos right now.')).toBeInTheDocument()
})
