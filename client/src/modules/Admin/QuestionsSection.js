import {
  List, ListItem, ListItemText, Paper, Typography
} from "@mui/material"
import { useEffect, useState } from "react"
import { apiFetch, getErrorMessage } from "../../api/client"

const formatDate = isoDate => new Date(isoDate).toLocaleString(undefined, {
  month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
})

// Questions are anonymous: the server never stores who asked, so there's no name to show
const QuestionsSection = () => {
  const [questions, setQuestions] = useState(null)
  const [error, setError] = useState("")

  useEffect(() => {
    apiFetch("/api/questions")
      .then(setQuestions)
      .catch(fetchError => {
        console.error('Error fetching questions:', fetchError)
        setError(getErrorMessage(fetchError, "Unable to load questions."))
      })
  }, [])

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>Questions Sent to the Admin</Typography>
      {error && <Typography variant="body2" color="error">{error}</Typography>}
      {!error && !questions && <Typography variant="body2" color="text.secondary">Loading questions...</Typography>}
      {questions?.length === 0 && <Typography variant="body2" color="text.secondary">No questions yet.</Typography>}
      {questions?.length > 0 && (
        <List>
          {questions.map(({ id, text, created_at }) => (
            <ListItem key={id} divider alignItems="flex-start">
              <ListItemText
                primary={text}
                secondary={formatDate(created_at)}
                primaryTypographyProps={{ sx: { whiteSpace: "pre-wrap" } }}
              />
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  )
}

export default QuestionsSection
