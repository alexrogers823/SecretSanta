import { ApiError, apiFetch, getErrorMessage, setAuthTokenProvider } from './client'

const jsonResponse = (status, data) => ({
  ok: status >= 200 && status < 300,
  status,
  headers: new Headers({ 'Content-Type': 'application/json' }),
  json: async () => data,
  text: async () => JSON.stringify(data),
})

beforeEach(() => {
  global.fetch = jest.fn()
  setAuthTokenProvider(async () => null)
})

test('calls the relative path and parses JSON', async () => {
  fetch.mockResolvedValue(jsonResponse(200, { message: 'hi' }))
  await expect(apiFetch('/api')).resolves.toEqual({ message: 'hi' })
  expect(fetch).toHaveBeenCalledWith('/api', { headers: {}, body: undefined })
})

test('sends no Authorization header when signed out', async () => {
  fetch.mockResolvedValue(jsonResponse(200, {}))
  await apiFetch('/api/photos')
  expect(fetch.mock.calls[0][1].headers.Authorization).toBeUndefined()
})

test('adds the ID token when signed in', async () => {
  setAuthTokenProvider(async () => 'id-token')
  fetch.mockResolvedValue(jsonResponse(200, {}))
  await apiFetch('/api/me')
  expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer id-token')
})

test('sends objects as JSON with the method and extra headers kept', async () => {
  fetch.mockResolvedValue(jsonResponse(200, {}))
  await apiFetch('/api/me', { method: 'PATCH', body: { address: '1 Elf Rd' }, headers: { 'X-Test': '1' } })
  expect(fetch).toHaveBeenCalledWith('/api/me', {
    method: 'PATCH',
    headers: { 'X-Test': '1', 'Content-Type': 'application/json' },
    body: JSON.stringify({ address: '1 Elf Rd' }),
  })
})

test('passes FormData and strings through untouched', async () => {
  fetch.mockResolvedValue(jsonResponse(200, {}))
  const form = new FormData()
  await apiFetch('/api/x', { method: 'POST', body: form })
  expect(fetch.mock.calls[0][1].body).toBe(form)
  expect(fetch.mock.calls[0][1].headers['Content-Type']).toBeUndefined()
})

test('returns text for non-JSON responses', async () => {
  fetch.mockResolvedValue({
    ok: true, status: 200, headers: new Headers({ 'Content-Type': 'text/html' }), text: async () => 'About text',
  })
  await expect(apiFetch('/api/about')).resolves.toBe('About text')
})

test('returns null for 204 No Content', async () => {
  fetch.mockResolvedValue({ ok: true, status: 204, headers: new Headers() })
  await expect(apiFetch('/api/photos/1', { method: 'DELETE' })).resolves.toBeNull()
})

test('throws ApiError with the server message and status', async () => {
  fetch.mockResolvedValue(jsonResponse(400, { error: 'address cannot be empty' }))
  const error = await apiFetch('/api/me').catch(e => e)
  expect(error).toBeInstanceOf(ApiError)
  expect(error.status).toBe(400)
  expect(error.message).toBe('address cannot be empty')
  expect(getErrorMessage(error)).toBe('address cannot be empty')
})

test('getErrorMessage falls back for network errors and errors without a message', async () => {
  expect(getErrorMessage(new TypeError('Failed to fetch'))).toBe('Something went wrong. Please try again.')
  expect(getErrorMessage(new ApiError('x', 500, '<html>'), 'Custom')).toBe('Custom')
})
