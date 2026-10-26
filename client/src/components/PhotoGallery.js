import DeleteIcon from '@mui/icons-material/Delete';
import {
  Alert, Dialog, DialogActions, DialogContent, DialogTitle, FormControl, IconButton, ImageList,
  ImageListItem, ImageListItemBar, InputLabel, MenuItem, Box as MuiBox, Paper, Select, Stack, Typography,
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { apiFetch, getErrorMessage } from '../api/client';
import { Button } from '../common';
import { useAuth } from '../context/AuthContext';

// Public: anyone can view the gallery, signed in or not. Members also see who posted each photo,
// and can delete their own (the admin can delete any). The signed URLs last an hour, so the
// list is fetched fresh each time the gallery loads rather than cached.
const PhotoGallery = () => {
  const { user } = useAuth()
  const [season, setSeason] = useState(null)  // null until chosen: the server defaults to this season
  const [gallery, setGallery] = useState(null)  // {season, seasons, photos}
  const [error, setError] = useState("")
  const [viewing, setViewing] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [deleteError, setDeleteError] = useState("")

  useEffect(() => {
    let cancelled = false
    apiFetch(season ? `/api/photos?season=${season}` : '/api/photos')
      .then(data => { if (!cancelled) { setGallery(data); setError("") } })
      .catch(fetchError => {
        console.error('Error fetching photos:', fetchError)
        if (!cancelled) setError(getErrorMessage(fetchError, "Unable to load photos right now."))
      })
    return () => { cancelled = true }
    // Signing in or out changes what the server includes (names, delete rights)
  }, [season, user?.id])

  const handleConfirmDelete = async () => {
    try {
      await apiFetch(`/api/photos/${deleting.id}`, { method: 'DELETE' })
      setGallery(current => ({ ...current, photos: current.photos.filter(photo => photo.id !== deleting.id) }))
      if (viewing?.id === deleting.id) setViewing(null)
      setDeleting(null)
      setDeleteError("")
    } catch (deleteFailure) {
      console.error('Error deleting photo:', deleteFailure)
      setDeleteError(getErrorMessage(deleteFailure))
    }
  }

  const photoAlt = photo => photo.owner_first_name ? `Christmas photo from ${photo.owner_first_name}` : 'Christmas photo'

  return (
    <Paper sx={{ p: 3 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
        <Typography variant="h6">Christmas Photos</Typography>
        {gallery?.seasons.length > 1 && (
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel id="photo-season-label">Season</InputLabel>
            <Select
              labelId="photo-season-label"
              label="Season"
              value={gallery.season}
              onChange={event => setSeason(event.target.value)}
            >
              {gallery.seasons.map(year => <MenuItem key={year} value={year}>{year}</MenuItem>)}
            </Select>
          </FormControl>
        )}
      </Stack>

      {error && <Alert severity="error">{error}</Alert>}
      {!error && !gallery && <Typography variant="body2" color="text.secondary">Loading photos...</Typography>}
      {gallery?.photos.length === 0 && (
        <Typography variant="body2" color="text.secondary">{`No photos from ${gallery.season} yet.`}</Typography>
      )}
      {gallery?.photos.length > 0 && (
        <ImageList cols={4} gap={8} sx={{ m: 0, gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr)) !important' }}>
          {gallery.photos.map(photo => (
            <ImageListItem key={photo.id} sx={{ cursor: 'pointer' }} onClick={() => setViewing(photo)}>
              <img src={photo.thumb_url} alt={photoAlt(photo)} loading="lazy" style={{ aspectRatio: '1', objectFit: 'cover' }} />
              {(photo.owner_first_name || photo.can_delete) && (
                <ImageListItemBar
                  title={photo.owner_first_name}
                  actionIcon={photo.can_delete && (
                    <IconButton
                      aria-label="Delete photo"
                      sx={{ color: 'common.white' }}
                      onClick={event => { event.stopPropagation(); setDeleting(photo) }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  )}
                />
              )}
            </ImageListItem>
          ))}
        </ImageList>
      )}

      <Dialog open={!!viewing} onClose={() => setViewing(null)} maxWidth="lg">
        {viewing && (
          <MuiBox component="img" src={viewing.display_url} alt={photoAlt(viewing)} sx={{ display: 'block', maxWidth: '100%', maxHeight: '85vh' }} />
        )}
      </Dialog>

      <Dialog open={!!deleting} onClose={() => { setDeleting(null); setDeleteError("") }}>
        <DialogTitle>Delete Photo</DialogTitle>
        <DialogContent>
          <Typography variant="body2">Are you sure you want to delete this photo? This cannot be undone.</Typography>
          {deleteError && <Typography variant="body2" color="error" sx={{ mt: 1 }}>{deleteError}</Typography>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setDeleting(null); setDeleteError("") }}>Cancel</Button>
          <Button color="error" onClick={handleConfirmDelete}>Delete</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  )
}

export default PhotoGallery
