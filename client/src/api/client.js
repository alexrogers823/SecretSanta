// One place for every call to the Flask API. Paths are relative ("/api/..."): in development
// the CRA proxy forwards them to Flask, and in production Firebase Hosting rewrites them to Cloud Run.

const GENERIC_ERROR = "Something went wrong. Please try again."

// Returns the signed-in user's Firebase ID token, or null when signed out.
// AuthContext plugs in Firebase's getIdToken once sign-in is wired up.
let getAuthToken = async () => null

export const setAuthTokenProvider = provider => {
  getAuthToken = provider
}

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.data = data
  }
}

// The server's error message for API errors, or a generic one for network failures and bugs
export const getErrorMessage = (error, fallback = GENERIC_ERROR) => (
  error instanceof ApiError && error.data?.error ? error.data.error : fallback
)

const isRawBody = body => (
  typeof body === "string" || body instanceof FormData || body instanceof Blob
)

export const apiFetch = async (path, { body, headers, ...options } = {}) => {
  const requestHeaders = { ...headers }

  const token = await getAuthToken()
  if (token) requestHeaders.Authorization = `Bearer ${token}`

  let requestBody = body
  if (body !== undefined && !isRawBody(body)) {
    requestHeaders["Content-Type"] = "application/json"
    requestBody = JSON.stringify(body)
  }

  const response = await fetch(path, { ...options, headers: requestHeaders, body: requestBody })

  let data = null
  if (response.status !== 204) {
    const isJson = response.headers.get("Content-Type")?.includes("application/json")
    data = isJson ? await response.json() : await response.text()
  }

  if (!response.ok) {
    throw new ApiError(data?.error || `Request failed with status ${response.status}`, response.status, data)
  }
  return data
}
