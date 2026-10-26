import { ApiError, apiFetch } from '../api/client'
import { PhotoValidationError, uploadPhotos } from './photoUpload'
import { getProfilePictureError, removeProfilePicture, uploadProfilePicture } from './profilePicture'
import { getContentType, runWithLimit } from './uploads'

jest.mock('../api/client', () => ({
  ...jest.requireActual('../api/client'),
  apiFetch: jest.fn(),
}))

const MB = 1024 * 1024
const photo = (name = 'a.jpg', type = 'image/jpeg', size = 1000) => ({ name, type, size })
const putOk = { ok: true, status: 200 }

beforeEach(() => {
  jest.clearAllMocks()
  global.fetch = jest.fn().mockResolvedValue(putOk)
})

const signedUploads = files => files.map((file, index) => ({
  photo_id: `p${index}-${file.filename}`,
  upload_url: `https://storage.example/upload/${file.filename}`,
  headers: { 'Content-Type': file.content_type, 'x-goog-content-length-range': `0,${15 * MB}` },
}))

// Shared helpers

test('getContentType falls back to the extension for HEIC photos', () => {
  expect(getContentType(photo('a.jpg', 'image/jpeg'))).toBe('image/jpeg')
  expect(getContentType(photo('IMG_1.HEIC', ''))).toBe('image/heic')
  expect(getContentType(photo('notes.txt', ''))).toBe('')
})

test('runWithLimit never runs more than the limit at once and keeps order', async () => {
  let running = 0
  let peak = 0
  const results = await runWithLimit([1, 2, 3, 4, 5, 6, 7], 3, async n => {
    running++
    peak = Math.max(peak, running)
    await new Promise(resolve => setTimeout(resolve, 5))
    running--
    return n * 10
  })
  expect(peak).toBe(3)
  expect(results).toEqual([10, 20, 30, 40, 50, 60, 70])
})

// Photos (2.14)

test('uploads each photo to its signed URL with the headers it was signed for', async () => {
  apiFetch.mockImplementation(async (path, { body }) => signedUploads(body.files))
  const files = [photo('a.jpg'), photo('b.png', 'image/png', 2000)]

  await expect(uploadPhotos(files)).resolves.toEqual([
    { photoId: 'p0-a.jpg', name: 'a.jpg', size: 1000 },
    { photoId: 'p1-b.png', name: 'b.png', size: 2000 },
  ])
  expect(apiFetch).toHaveBeenCalledWith('/api/photos/uploads', {
    method: 'POST',
    body: { files: [
      { filename: 'a.jpg', content_type: 'image/jpeg', size: 1000 },
      { filename: 'b.png', content_type: 'image/png', size: 2000 },
    ] },
  })
  expect(fetch).toHaveBeenCalledWith('https://storage.example/upload/a.jpg', {
    method: 'PUT',
    headers: { 'Content-Type': 'image/jpeg', 'x-goog-content-length-range': `0,${15 * MB}` },
    body: files[0],
  })
})

test('more than 10 photos are requested in batches of 10', async () => {
  apiFetch.mockImplementation(async (path, { body }) => signedUploads(body.files))
  const files = Array.from({ length: 23 }, (_, n) => photo(`${n}.jpg`))
  const results = await uploadPhotos(files)
  expect(apiFetch.mock.calls.map(([, { body }]) => body.files.length)).toEqual([10, 10, 3])
  expect(results).toHaveLength(23)
  expect(fetch).toHaveBeenCalledTimes(23)
})

test.each([
  [[photo('a.gif', 'image/gif')], "a.gif isn't a JPEG, PNG, WebP or HEIC photo"],
  [[photo('big.jpg', 'image/jpeg', 15 * MB + 1)], 'big.jpg is larger than 15 MB'],
  [Array.from({ length: 26 }, (_, n) => photo(`${n}.jpg`)), 'You can upload up to 25 photos per season'],
])('rejects invalid selections before contacting the server', async (files, message) => {
  const error = await uploadPhotos(files).catch(e => e)
  expect(error).toBeInstanceOf(PhotoValidationError)
  expect(error.message).toBe(message)
  expect(apiFetch).not.toHaveBeenCalled()
})

test('a server limit error is passed through', async () => {
  const limit = 'you can upload 25 photos per season, and have 2 left'
  apiFetch.mockRejectedValue(new ApiError(limit, 400, { error: limit }))
  await expect(uploadPhotos([photo(), photo(), photo()])).rejects.toThrow(limit)
  expect(fetch).not.toHaveBeenCalled()
})

test('a failed PUT rejects', async () => {
  apiFetch.mockImplementation(async (path, { body }) => signedUploads(body.files))
  fetch.mockResolvedValue({ ok: false, status: 403 })
  await expect(uploadPhotos([photo()])).rejects.toThrow('Upload failed with status 403')
})

// Profile pictures (2.17)

test('profile picture checks match the server limits', () => {
  expect(getProfilePictureError(photo('a.gif', 'image/gif'))).toBe('')
  expect(getProfilePictureError(photo('IMG.heic', ''))).toBe('')
  expect(getProfilePictureError(photo('a.bmp', 'image/bmp'))).toMatch(/must be a JPEG/)
  expect(getProfilePictureError(photo('a.jpg', 'image/jpeg', 5 * MB + 1))).toBe('Profile picture must be 5 MB or smaller')
})

test('uploads the picture and waits for processing to set it', async () => {
  const upload = { picture_id: 'pic9', upload_url: 'https://storage.example/pic', headers: { 'Content-Type': 'image/png' } }
  const before = { id: 'u1', profile_picture_url: null }
  const after = { id: 'u1', profile_picture_url: 'https://storage.example/avatars/u1/pic9.webp?sig' }
  apiFetch
    .mockResolvedValueOnce(upload)
    .mockResolvedValueOnce(before)
    .mockResolvedValueOnce(before)
    .mockResolvedValueOnce(after)

  const file = photo('me.png', 'image/png')
  await expect(uploadProfilePicture('u1', file, { pollIntervalMs: 0 })).resolves.toEqual(after)

  expect(apiFetch).toHaveBeenNthCalledWith(1, '/api/me/profile-picture', { method: 'POST', body: { content_type: 'image/png', size: 1000 } })
  expect(fetch).toHaveBeenCalledWith('https://storage.example/pic', { method: 'PUT', headers: { 'Content-Type': 'image/png' }, body: file })
  expect(apiFetch).toHaveBeenCalledTimes(4)  // the upload request, then /api/me until the picture appears
})

test('gives up polling after the window and returns the current profile', async () => {
  apiFetch
    .mockResolvedValueOnce({ picture_id: 'pic9', upload_url: 'https://x', headers: {} })
    .mockResolvedValue({ id: 'u1', profile_picture_url: null })

  await expect(uploadProfilePicture('u1', photo('me.png', 'image/png'), { pollIntervalMs: 0 }))
    .resolves.toEqual({ id: 'u1', profile_picture_url: null })
  expect(apiFetch).toHaveBeenCalledTimes(1 + 15)
})

test('removing the picture calls the API and returns the profile', async () => {
  apiFetch.mockResolvedValue({ id: 'u1', profile_picture_url: null })
  await expect(removeProfilePicture('u1')).resolves.toEqual({ id: 'u1', profile_picture_url: null })
  expect(apiFetch).toHaveBeenCalledWith('/api/me/profile-picture', { method: 'DELETE' })
})
