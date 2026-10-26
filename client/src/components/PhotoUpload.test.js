import { act, fireEvent, render, screen } from '@testing-library/react'
import { ApiError } from '../api/client'
import { PhotoValidationError, uploadPhotos } from '../utils/photoUpload'
import PhotoUpload from './PhotoUpload'

jest.mock('../utils/photoUpload', () => ({
  ...jest.requireActual('../utils/photoUpload'),
  uploadPhotos: jest.fn(),
}))

const file = name => new File(['x'], name, { type: 'image/jpeg' })

beforeEach(() => {
  jest.clearAllMocks()
  global.URL.createObjectURL = jest.fn(f => `blob:${f.name}`)
  global.URL.revokeObjectURL = jest.fn()
})

const choose = async files => {
  await act(async () => {
    fireEvent.change(document.querySelector('input[type="file"]'), { target: { files } })
  })
}

test('the picker accepts the server photo formats, including HEIC', () => {
  render(<PhotoUpload />)
  const accept = document.querySelector('input[type="file"]').getAttribute('accept').split(',')
  expect(accept).toEqual(expect.arrayContaining(['image/jpeg', 'image/png', 'image/webp', 'image/heic', '.heic']))
  expect(document.querySelector('input[type="file"]')).toHaveAttribute('multiple')
})

test('success says photos appear in the gallery shortly, with local previews', async () => {
  uploadPhotos.mockResolvedValue([{ photoId: 'p1', name: 'a.jpg', size: 1 }, { photoId: 'p2', name: 'b.jpg', size: 1 }])
  render(<PhotoUpload />)
  const files = [file('a.jpg'), file('b.jpg')]
  await choose(files)

  expect(uploadPhotos).toHaveBeenCalledWith(files)
  expect(screen.getByText("Uploaded 2 photos! They'll appear in the gallery shortly.")).toBeInTheDocument()
  expect(screen.getAllByRole('img').map(img => img.getAttribute('src'))).toEqual(['blob:a.jpg', 'blob:b.jpg'])
})

test('one photo gets singular wording', async () => {
  uploadPhotos.mockResolvedValue([{ photoId: 'p1', name: 'a.jpg', size: 1 }])
  render(<PhotoUpload />)
  await choose([file('a.jpg')])
  expect(screen.getByText("Uploaded 1 photo! It'll appear in the gallery shortly.")).toBeInTheDocument()
})

test('shows the button as busy while uploading', async () => {
  let finish
  uploadPhotos.mockReturnValue(new Promise(resolve => { finish = resolve }))
  render(<PhotoUpload />)
  await choose([file('a.jpg')])
  expect(screen.getByText('Uploading...')).toBeInTheDocument()
  await act(async () => finish([]))
  expect(screen.getByText('Upload')).toBeInTheDocument()
})

test('browser-side problems are shown as they are', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  uploadPhotos.mockRejectedValue(new PhotoValidationError('big.jpg is larger than 15 MB'))
  render(<PhotoUpload />)
  await choose([file('big.jpg')])
  expect(screen.getByText('big.jpg is larger than 15 MB')).toBeInTheDocument()
})

test('server limits are shown as they are', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  const limit = 'you can upload 25 photos per season, and have 0 left'
  uploadPhotos.mockRejectedValue(new ApiError(limit, 400, { error: limit }))
  render(<PhotoUpload />)
  await choose([file('a.jpg')])
  expect(screen.getByText(limit)).toBeInTheDocument()
})

test('other failures get the generic message', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  uploadPhotos.mockRejectedValue(new Error('Upload failed with status 403'))
  render(<PhotoUpload />)
  await choose([file('a.jpg')])
  expect(screen.getByText('Upload failed, please try again')).toBeInTheDocument()
})
