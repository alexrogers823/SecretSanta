import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { Form } from "../common"
import { uploadProfilePicture } from "../utils/profilePicture"
import ProfilePictureInput from "./ProfilePictureInput"

const SignupForm = ({ onSignupSuccess }) => {
  const [error, setError] = useState("")
  const [profilePicture, setProfilePicture] = useState(null)

  const handleSignupSubmit = async ({ first_name, last_name, email, address }) => {
    if (!first_name?.trim() || !last_name?.trim() || !email?.trim() || !address?.trim()) {
      setError("First name, last name, email, and address are required.")
      return
    }

    try {
      const response = await fetch("http://localhost:8000/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ first_name, last_name, email, address }),
      })
      const data = await response.json()

      if (response.ok) {
        setError("")
        let signedUpUser = data
        if (profilePicture) {
          try {
            signedUpUser = await uploadProfilePicture(data.id, profilePicture)
          } catch (uploadError) {
            // The account already exists, so continue; the picture can be added later from Edit
            console.error('Error uploading profile picture:', uploadError)
          }
        }
        onSignupSuccess?.(signedUpUser)
      } else {
        setError(data.error || "Something went wrong. Please try again.")
      }
    } catch (error) {
      console.error('Error signing up:', error)
      setError("Something went wrong. Please try again.")
    }
  }

  return (
    <Form
      title="Sign Up for Secret Santa"
      submitButtonText="Register"
      onSubmit={handleSignupSubmit}
      noValidate
    >
      <TextField id="first_name" label="First Name" variant="standard" required />
      <TextField id="last_name" label="Last Name" variant="standard" required />
      <TextField id="email" label="Email" variant="standard" required />
      <TextField id="address" label="Address" variant="standard" multiline required fullWidth />
      <ProfilePictureInput file={profilePicture} onChange={setProfilePicture} />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default SignupForm
