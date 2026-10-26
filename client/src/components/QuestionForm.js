import { TextField, Typography } from '@mui/material';
import React, { useState } from 'react';
import { apiFetch, getErrorMessage } from '../api/client';
import { Form } from '../common';

const MAX_QUESTION_LENGTH = 2000 // matches the server limit

const QuestionForm = ({ onSent }) => {
  const [error, setError] = useState("")
  const [sending, setSending] = useState(false)

  const handleSubmit = async ({ text }) => {
    if (!text?.trim()) {
      setError("Please write your question first.")
      return
    }
    if (text.length > MAX_QUESTION_LENGTH) {
      setError(`Questions can be up to ${MAX_QUESTION_LENGTH} characters.`)
      return
    }

    setSending(true)
    try {
      await apiFetch("/api/questions", { method: "POST", body: { text } })
      setError("")
      onSent?.()
    } catch (error) {
      console.error('Error sending question:', error)
      setError(getErrorMessage(error))
    } finally {
      setSending(false)
    }
  }

  return (
    <Form
      title="Questions of clarifications for Bro. T4ought"
      submitButtonText={sending ? "Sending..." : "Submit Question"}
      onSubmit={handleSubmit}
      noValidate
    >
      <Typography variant="body2" color="text.secondary" gutterBottom>
        Your question is sent anonymously. Your name isn't attached to it, not even for the admin.
      </Typography>
      <TextField id="text" label="Your question" variant="standard" multiline minRows={3} required fullWidth />
      {error && <Typography color="error" variant="body2">{error}</Typography>}
    </Form>
  )
}

export default QuestionForm
