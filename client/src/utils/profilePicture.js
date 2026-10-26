import { apiFetch } from '../api/client'
import { getContentType, putToSignedUrl } from './uploads'

// Keep in sync with flask_server/profile_pictures.py
export const MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024
export const PROFILE_PICTURE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/heic']

// The picture is processed in the background (cropped, location data removed) before it shows up
const POLL_INTERVAL_MS = 1000
const POLL_ATTEMPTS = 15

export const getProfilePictureError = file => {
  if (!PROFILE_PICTURE_TYPES.includes(getContentType(file))) return "Profile picture must be a JPEG, PNG, GIF, WebP, or HEIC image"
  if (file.size > MAX_PROFILE_PICTURE_BYTES) return "Profile picture must be 5 MB or smaller"
  return ""
}

const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

// Uploads the signed-in user's picture and resolves with their updated profile. If processing
// takes longer than the polling window, it resolves with the profile as it is; the new picture
// appears on the next page load. (userId is kept for callers; the API uses the signed-in user.)
export const uploadProfilePicture = async (userId, file, { pollIntervalMs = POLL_INTERVAL_MS } = {}) => {
  const upload = await apiFetch('/api/me/profile-picture', {
    method: 'POST',
    body: { content_type: getContentType(file), size: file.size },
  })
  await putToSignedUrl(upload, file)

  let user
  for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt++) {
    user = await apiFetch('/api/me')
    if (user.profile_picture_url?.includes(upload.picture_id)) return user
    await wait(pollIntervalMs)
  }
  return user
}

export const removeProfilePicture = async userId => apiFetch('/api/me/profile-picture', { method: 'DELETE' })
