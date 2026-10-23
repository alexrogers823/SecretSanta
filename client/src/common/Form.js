import { Paper, Stack, Typography } from "@mui/material"
import { useRef, useState } from "react"
import Button from "./Button"

const Form = ({ title, submitButtonText, actions, children, square, onSubmit, ...rest }) => {
  const [formData, setFormData] = useState({})
  const formRef = useRef(null)

  const handleSubmit = e => {
    e.preventDefault()

    const inputs = formRef.current.querySelectorAll('.MuiInput-input')
    const collected = {}

    inputs.forEach(input => {
      const { id, value } = input
      collected[id] = value
    })

    setFormData(collected)
    onSubmit?.(collected)
  }

  return (
    <Paper ref={formRef} component="form" onSubmit={handleSubmit} square={square || false} {...rest}>
      <Typography variant="h6" gutterBottom>{title}</Typography>
      {children}
      <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
        {actions}
        <Button type="submit">{submitButtonText || "Submit"}</Button>
      </Stack>
    </Paper>
  )
}

export default Form