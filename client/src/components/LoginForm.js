import { TextField, Typography } from "@mui/material"
import { useState } from "react"
import { Form } from "../common"
import { useAuth } from "../context/AuthContext"

const COPY = {
  login: {
    title: "Log In to Secret Santa",
    intro: "Enter your email and we'll send you a link to log in. No password needed.",
    submit: "Email Me a Link",
  },
  signup: {
    title: "Sign Up for Secret Santa",
    intro: "Enter the email you were invited with. We'll send you a link to finish signing up.",
    submit: "Email Me a Link",
  },
  confirm: {
    title: "Confirm Your Email",
    intro: "It looks like you opened the sign-in link on a different device. Enter the email the link was sent to.",
    submit: "Log In",
  },
}

const LINK_ERRORS = {
  'auth/invalid-action-code': "This sign-in link has expired or was already used. Request a new one.",
  'auth/invalid-email': "That email address doesn't look right.",
}

// Passwordless sign-in: emails a one-time link (mode "login" or "signup"), or, in mode
// "confirm", finishes sign-in from a link that was opened on a different device
const LoginForm = ({ mode = "login", onConfirmed, initialError = "" }) => {
  const { sendSignInLink, completeSignIn } = useAuth()
  const [error, setError] = useState(initialError)
  const [sentTo, setSentTo] = useState("")
  const copy = COPY[mode]

  const handleSubmit = async ({ email }) => {
    const address = email?.trim()
    if (!address) {
      setError("Email is required.")
      return
    }

    try {
      if (mode === "confirm") {
        await completeSignIn(address)
        onConfirmed?.()
      } else {
        await sendSignInLink(address)
        setSentTo(address)
      }
      setError("")
    } catch (error) {
      console.error('Error with sign-in link:', error)
      setError(LINK_ERRORS[error.code] || "Something went wrong. Please try again.")
    }
  }

  if (sentTo) {
    return (
      <Form title="Check Your Email" submitButtonText="Use a Different Email" onSubmit={() => setSentTo("")}>
        <Typography variant="body2">
          {`We sent a sign-in link to ${sentTo}. Open it on this device to continue.`}
        </Typography>
      </Form>
    )
  }

  return (
    <Form title={copy.title} submitButtonText={copy.submit} onSubmit={handleSubmit} noValidate>
      <Typography variant="body2" gutterBottom>{copy.intro}</Typography>
      <TextField id="email" label="Email" type="email" variant="standard" autoComplete="email" required fullWidth />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default LoginForm
