export const MAX_PROFILE_PICTURE_BYTES = 5 * 1024 * 1024
export const PROFILE_PICTURE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']

export const getProfilePictureError = file => {
  if (!PROFILE_PICTURE_TYPES.includes(file.type)) return "Profile picture must be a JPEG, PNG, GIF, or WebP image"
  if (file.size > MAX_PROFILE_PICTURE_BYTES) return "Profile picture must be 5 MB or smaller"
  return ""
}

// Stored on the Flask server's disk for now; moves to the private profile-pictures bucket on GCP
export const uploadProfilePicture = async (userId, file) => {
  const body = new FormData()
  body.append('profile_picture', file)

  const response = await fetch(`http://localhost:8000/api/users/${userId}/profile-picture`, { method: "PUT", body })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || "Profile picture upload failed")
  return data
}

export const removeProfilePicture = async userId => {
  const response = await fetch(`http://localhost:8000/api/users/${userId}/profile-picture`, { method: "DELETE" })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || "Unable to remove profile picture")
  return data
}
