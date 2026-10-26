import { Avatar, Stack, Typography } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { Button } from '../common';
import { getProfilePictureError, PROFILE_PICTURE_TYPES } from '../utils/profilePicture';

const ProfilePictureInput = ({ file, existingUrl, onChange, onRemoveExisting }) => {
  const [previewUrl, setPreviewUrl] = useState(null)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  const handleFileSelected = e => {
    const selected = e.target.files?.[0]
    e.target.value = ""
    if (!selected) return

    const validationError = getProfilePictureError(selected)
    setError(validationError)
    if (!validationError) onChange(selected)
  }

  const handleRemove = () => {
    setError("")
    if (file) {
      onChange(null)
    } else {
      onRemoveExisting?.()
    }
  }

  const shownUrl = previewUrl || existingUrl

  return (
    <Stack spacing={1} sx={{ mt: 2 }}>
      <Typography variant="body2" color="text.secondary">Profile Picture (optional)</Typography>
      <Stack direction="row" spacing={2} alignItems="center">
        <Avatar src={shownUrl || undefined} alt="Profile picture preview" sx={{ width: 64, height: 64 }} />
        <Button component="label" size="small">
          {shownUrl ? "Change Photo" : "Choose Photo"}
          <input hidden type="file" accept={[...PROFILE_PICTURE_TYPES, '.heic', '.heif'].join(',')} onChange={handleFileSelected} />
        </Button>
        {shownUrl && <Button size="small" color="error" onClick={handleRemove}>Remove</Button>}
      </Stack>
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Stack>
  )
}

export default ProfilePictureInput
