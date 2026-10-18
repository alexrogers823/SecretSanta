const MOCK_UPLOAD_DELAY_MS = 1200

// Mocked until the app is hooked up to Google Cloud Storage (see GCP_MIGRATION_PLAN.md).
// Swap the body for a real upload (e.g. a signed URL from the API, then PUT each file to the bucket).
export const uploadPhotos = files => new Promise(resolve => {
  setTimeout(() => {
    resolve(files.map(file => ({ name: file.name, size: file.size })))
  }, MOCK_UPLOAD_DELAY_MS)
})
