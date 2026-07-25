import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { Form } from "../common"

const SignupForm = ({ onSignupSuccess }) => {
  const [error, setError] = useState("")

  const handleSignupSubmit = async ({ name, email }) => {
    if (!name?.trim() || !email?.trim()) {
      setError("Name and email are required.")
      return
    }

    try {
      const response = await fetch("http://localhost:8000/api/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email }),
      })
      const data = await response.json()

      if (response.ok) {
        setError("")
        onSignupSuccess?.(data)
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
      <TextField id="name" label="Name" variant="standard" required />
      <TextField id="email" label="Email" variant="standard" required />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default SignupForm
