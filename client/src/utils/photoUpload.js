import { apiFetch } from '../api/client'
import { getContentType, putToSignedUrl, runWithLimit } from './uploads'

// Keep in sync with flask_server/photo_storage.py
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic']
export const MAX_PHOTO_BYTES = 15 * 1024 * 1024
export const MAX_PHOTOS_PER_SEASON = 25
const MAX_FILES_PER_REQUEST = 10
const PARALLEL_UPLOADS = 3

export class PhotoValidationError extends Error {}

export const getPhotoError = file => {
  if (!PHOTO_TYPES.includes(getContentType(file))) return `${file.name} isn't a JPEG, PNG, WebP or HEIC photo`
  if (file.size > MAX_PHOTO_BYTES) return `${file.name} is larger than 15 MB`
  return ""
}

const chunk = (items, size) => Array.from(
  { length: Math.ceil(items.length / size) },
  (_, index) => items.slice(index * size, (index + 1) * size),
)

// Asks the API for one signed upload URL per photo, then sends each photo straight to the
// bucket. The server re-checks every limit, including the per-season count.
// Resolves with [{photoId, name, size}].
export const uploadPhotos = async files => {
  const invalid = files.map(getPhotoError).find(Boolean)
  if (invalid) throw new PhotoValidationError(invalid)
  if (files.length > MAX_PHOTOS_PER_SEASON) {
    throw new PhotoValidationError(`You can upload up to ${MAX_PHOTOS_PER_SEASON} photos per season`)
  }

  const results = []
  for (const batch of chunk(files, MAX_FILES_PER_REQUEST)) {
    const uploads = await apiFetch('/api/photos/uploads', {
      method: 'POST',
      body: { files: batch.map(file => ({ filename: file.name, content_type: getContentType(file), size: file.size })) },
    })
    await runWithLimit(batch, PARALLEL_UPLOADS, (file, index) => putToSignedUrl(uploads[index], file))
    results.push(...batch.map((file, index) => ({ photoId: uploads[index].photo_id, name: file.name, size: file.size })))
  }
  return results
}
