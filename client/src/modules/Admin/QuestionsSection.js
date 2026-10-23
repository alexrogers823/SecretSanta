import {
  List, ListItem, ListItemText, Paper, Typography
} from "@mui/material"

const MOCK_QUESTIONS = [
  {
    id: 1,
    name: "Jane Doe",
    email: "jane@example.com",
    question: "Is there a spending limit for gifts this year?",
  },
  {
    id: 2,
    name: "John Smith",
    email: "john@example.com",
    question: "When do assignments get revealed?",
  },
]

const QuestionsSection = () => (
  <Paper sx={{ p: 2, mt: 2 }}>
    <Typography variant="h6" gutterBottom>Questions Sent to the Admin</Typography>
    <Typography variant="body2" color="text.secondary" gutterBottom>
      This is a UI preview only — these questions aren't wired up to real submissions yet.
    </Typography>
    <List>
      {MOCK_QUESTIONS.map(({ id, name, email, question }) => (
        <ListItem key={id} divider alignItems="flex-start">
          <ListItemText
            primary={question}
            secondary={`${name} (${email})`}
          />
        </ListItem>
      ))}
    </List>
  </Paper>
)

export default QuestionsSection
