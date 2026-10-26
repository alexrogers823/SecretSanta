import { Alert, CircularProgress, Box as MuiBox, Stack } from '@mui/material';
import React, { useEffect, useState } from 'react';
import { Button, PromptCard } from '../common';
import { getErrorMessage } from '../api/client';
import { PHOTO_TYPES, PhotoValidationError, uploadPhotos } from '../utils/photoUpload';

const PhotoUpload = () => {
  const [uploading, setUploading] = useState(false)
  const [uploaded, setUploaded] = useState([])
  const [error, setError] = useState("")

  useEffect(() => {
    return () => uploaded.forEach(photo => URL.revokeObjectURL(photo.previewUrl))
  }, [uploaded])

  const handleFilesSelected = async e => {
    const files = Array.from(e.target.files || [])
    e.target.value = ""
    if (files.length === 0) return

    setError("")
    setUploading(true)
    try {
      const results = await uploadPhotos(files)
      // Previews come from the user's own files, so they're safe to show before processing finishes
      setUploaded(results.map((result, index) => ({ ...result, previewUrl: URL.createObjectURL(files[index]) })))
    } catch (err) {
      console.error('Error uploading photos:', err)
      // Show size/type problems and server limits (e.g. 25 photos per season) as they are
      setError(err instanceof PhotoValidationError ? err.message : getErrorMessage(err, "Upload failed, please try again"))
    } finally {
      setUploading(false)
    }
  }

  return (
    <PromptCard message="Upload your best Christmas photos of you and the family for the LBs to see">
      <Button
        component="label"
        variant="contained"
        disabled={uploading}
        startIcon={uploading ? <CircularProgress size={16} color="inherit" /> : null}
      >
        {uploading ? "Uploading..." : "Upload"}
        <input hidden type="file" accept={[...PHOTO_TYPES, '.heic', '.heif'].join(',')} multiple onChange={handleFilesSelected} />
      </Button>
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
      {uploaded.length > 0 && (
        <>
          <Alert severity="success" sx={{ mt: 2 }}>
            {`Uploaded ${uploaded.length} photo${uploaded.length === 1 ? "" : "s"}! ${uploaded.length === 1 ? "It" : "They"}'ll appear in the gallery shortly.`}
          </Alert>
          <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
            {uploaded.map(photo => (
              <MuiBox
                key={photo.previewUrl}
                component="img"
                src={photo.previewUrl}
                alt={photo.name}
                sx={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 1 }}
              />
            ))}
          </Stack>
        </>
      )}
    </PromptCard>
  )
}

export default PhotoUpload
