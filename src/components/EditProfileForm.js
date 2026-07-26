import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { Form } from "../common"

const EditProfileForm = ({ user, onEditSuccess }) => {
  const [error, setError] = useState("")

  const handleEditSubmit = async ({ name, email, address }) => {
    if (!name?.trim() || !email?.trim() || !address?.trim()) {
      setError("Name, email, and address are required.")
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/api/users/${user.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, address }),
      })
      const data = await response.json()

      if (response.ok) {
        setError("")
        onEditSuccess?.(data)
      } else {
        setError(data.error || "Something went wrong. Please try again.")
      }
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
      <TextField id="name" label="Name" variant="standard" defaultValue={user.name} required />
      <TextField id="email" label="Email" variant="standard" defaultValue={user.email} required />
      <TextField id="address" label="Address" variant="standard" defaultValue={user.address} multiline required fullWidth />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default EditProfileForm
