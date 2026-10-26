import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { getErrorMessage } from "../api/client"
import { Button, Form } from "../common"
import { useAuth } from "../context/AuthContext"
import { uploadProfilePicture } from "../utils/profilePicture"
import ProfilePictureInput from "./ProfilePictureInput"

// Shown after the first sign-in: the email is already verified by the link, so this
// only asks for the rest of the profile
const SignupForm = ({ onSignupSuccess }) => {
  const { email, createProfile, logout } = useAuth()
  const [error, setError] = useState("")
  const [profilePicture, setProfilePicture] = useState(null)

  const handleSignupSubmit = async ({ first_name, last_name, address }) => {
    if (!first_name?.trim() || !last_name?.trim() || !address?.trim()) {
      setError("First name, last name, and address are required.")
      return
    }

    let signedUpUser
    try {
      signedUpUser = await createProfile({ first_name, last_name, address })
    } catch (error) {
      console.error('Error signing up:', error)
      setError(getErrorMessage(error))
      return
    }

    setError("")
    if (profilePicture) {
      try {
        signedUpUser = { ...signedUpUser, ...await uploadProfilePicture(signedUpUser.id, profilePicture) }
      } catch (uploadError) {
        // The profile already exists, so continue; the picture can be added later from Edit
        console.error('Error uploading profile picture:', uploadError)
      }
    }
    onSignupSuccess?.(signedUpUser)
  }

  return (
    <Form
      title="Finish Signing Up"
      submitButtonText="Register"
      onSubmit={handleSignupSubmit}
      actions={<Button onClick={logout}>Use a Different Email</Button>}
      noValidate
    >
      <TextField id="email" label="Email" variant="standard" value={email || ""} slotProps={{ input: { readOnly: true } }} fullWidth />
      <TextField id="first_name" label="First Name" variant="standard" required />
      <TextField id="last_name" label="Last Name" variant="standard" required />
      <TextField id="address" label="Address" variant="standard" multiline required fullWidth />
      <ProfilePictureInput file={profilePicture} onChange={setProfilePicture} />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default SignupForm
