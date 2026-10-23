import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { Form } from "../common"
import { removeProfilePicture, uploadProfilePicture } from "../utils/profilePicture"
import ProfilePictureInput from "./ProfilePictureInput"

const EditProfileForm = ({ user, onEditSuccess }) => {
  const [error, setError] = useState("")
  const [profilePicture, setProfilePicture] = useState(null)
  const [removeExistingPicture, setRemoveExistingPicture] = useState(false)

  const handleEditSubmit = async ({ first_name, last_name, email, address }) => {
    if (!first_name?.trim() || !last_name?.trim() || !email?.trim() || !address?.trim()) {
      setError("First name, last name, email, and address are required.")
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/api/users/${user.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ first_name, last_name, email, address }),
      })
      const data = await response.json()

      if (!response.ok) {
        setError(data.error || "Something went wrong. Please try again.")
        return
      }

      let updatedUser = data
      if (profilePicture) {
        updatedUser = await uploadProfilePicture(user.id, profilePicture)
      } else if (removeExistingPicture && user.profile_picture_url) {
        updatedUser = await removeProfilePicture(user.id)
      }

      setError("")
      onEditSuccess?.(updatedUser)
    } catch (error) {
      console.error('Error updating profile:', error)
      setError("Something went wrong. Please try again.")
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
      <TextField id="email" label="Email" variant="standard" defaultValue={user.email} required />
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
