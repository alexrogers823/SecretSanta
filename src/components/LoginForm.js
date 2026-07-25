import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { Form } from "../common"

const LoginForm = ({ onLoginSuccess }) => {
  const [error, setError] = useState("")

  const handleLoginSubmit = async ({ name, email }) => {
    try {
      const params = new URLSearchParams({ name, email })
      const response = await fetch(`http://localhost:8000/api/users?${params}`)
      const users = response.ok ? await response.json() : []

      if (users.length > 0) {
        setError("")
        onLoginSuccess?.(users[0].name)
      } else {
        setError("No matching user found — check your name and email.")
      }
    } catch (error) {
      console.error('Error logging in:', error)
      setError("No matching user found — check your name and email.")
    }
  }

  return (
    <Form
      title="Log In to Secret Santa Profile"
      submitButtonText="Log In"
      onSubmit={handleLoginSubmit}
    >
      {/* make dropdown of already registered brothers as name field  */}
      <TextField id="name" label="Name" variant="standard" required />
      <TextField id="email" label="email" variant="standard" required />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default LoginForm
