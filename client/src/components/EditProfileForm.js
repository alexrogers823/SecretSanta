import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { apiFetch, getErrorMessage } from "../api/client"
import { Form } from "../common"
import { removeProfilePicture, uploadProfilePicture } from "../utils/profilePicture"
import ProfilePictureInput from "./ProfilePictureInput"

const EditProfileForm = ({ user, onEditSuccess }) => {
  const [error, setError] = useState("")
  const [profilePicture, setProfilePicture] = useState(null)
  const [removeExistingPicture, setRemoveExistingPicture] = useState(false)

  const handleEditSubmit = async ({ first_name, last_name, address }) => {
    if (!first_name?.trim() || !last_name?.trim() || !address?.trim()) {
      setError("First name, last name, and address are required.")
      return
    }

    try {
      let updatedUser = await apiFetch("/api/me", { method: "PATCH", body: { first_name, last_name, address } })
      if (profilePicture) {
        updatedUser = await uploadProfilePicture(user.id, profilePicture)
      } else if (removeExistingPicture && user.profile_picture_url) {
        updatedUser = await removeProfilePicture(user.id)
      }

      setError("")
      onEditSuccess?.(updatedUser)
    } catch (error) {
      console.error('Error updating profile:', error)
      setError(getErrorMessage(error))
    }
  }

  return (
    <Form
      title="Edit Your Information"
      submitButtonText="Save"
      onSubmit={handleEditSubmit}
      noValidate
    >
      <TextField id="first_name" label="First Name" variant="standard" defaultValue={user.first_name} required />
      <TextField id="last_name" label="Last Name" variant="standard" defaultValue={user.last_name || ''} required />
      {/* The email is the one you sign in with, so it can't be changed here */}
      <TextField id="email" label="Email" variant="standard" defaultValue={user.email} slotProps={{ input: { readOnly: true } }} />
      <TextField id="address" label="Address" variant="standard" defaultValue={user.address} multiline required fullWidth />
      <ProfilePictureInput
        file={profilePicture}
        existingUrl={removeExistingPicture ? null : user.profile_picture_url}
        onChange={setProfilePicture}
        onRemoveExisting={() => setRemoveExistingPicture(true)}
      />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default EditProfileForm
