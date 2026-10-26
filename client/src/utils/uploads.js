// Helpers for uploading straight to the storage bucket with a signed URL from the API

// Chrome and Firefox report iPhone HEIC photos with an empty type, so fall back to the extension
export const getContentType = file => {
  if (file.type) return file.type
  return /\.(heic|heif)$/i.test(file.name) ? 'image/heic' : ''
}

// The signed URL only accepts the exact headers it was created with
export const putToSignedUrl = async ({ upload_url, headers }, file) => {
  const response = await fetch(upload_url, { method: 'PUT', headers, body: file })
  if (!response.ok) throw new Error(`Upload failed with status ${response.status}`)
}

// Runs task(item) for every item with at most `limit` running at once, keeping result order
export const runWithLimit = async (items, limit, task) => {
  const results = new Array(items.length)
  let next = 0
  const worker = async () => {
    while (next < items.length) {
      const index = next++
      results[index] = await task(items[index], index)
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker))
  return results
}
