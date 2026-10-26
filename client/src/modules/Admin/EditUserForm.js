import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { apiFetch, getErrorMessage } from "../../api/client"
import { Form } from "../../common"
import { getFullName } from "../../utils/userHelpers"

const EditUserForm = ({ user, onEditSuccess }) => {
  const [error, setError] = useState("")

  const handleEditSubmit = async ({ first_name, last_name, email, address }) => {
    if (!first_name?.trim() || !last_name?.trim() || !email?.trim() || !address?.trim()) {
      setError("First name, last name, email, and address are required.")
      return
    }

    try {
      const data = await apiFetch(`/api/users/${user.id}`, {
        method: "PATCH",
        body: { first_name, last_name, email, address },
      })
      setError("")
      onEditSuccess?.(data)
    } catch (error) {
      console.error('Error updating user:', error)
      setError(getErrorMessage(error))
    }
  }

  return (
    <Form
      title={`Edit ${getFullName(user)}`}
      submitButtonText="Save"
      onSubmit={handleEditSubmit}
      noValidate
    >
      <TextField id="first_name" label="First Name" variant="standard" defaultValue={user.first_name} required />
      <TextField id="last_name" label="Last Name" variant="standard" defaultValue={user.last_name || ''} required />
      <TextField id="email" label="Email" variant="standard" defaultValue={user.email} required />
      <TextField id="address" label="Address" variant="standard" defaultValue={user.address} multiline required fullWidth />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default EditUserForm
