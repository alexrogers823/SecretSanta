import { Alert, Paper, Snackbar, Stack, Typography } from '@mui/material';
import React, { useState } from 'react';
import { Button, Modal } from '../common';
import { useAuth } from '../context/AuthContext';
import { useAuthModal } from '../context/AuthModalContext';
import QuestionForm from './QuestionForm';

const QuestionsPrompt = () => {
  const { user } = useAuth()
  const { openLogin } = useAuthModal()
  const [openQuestionModal, setOpenQuestionModal] = useState(false)
  const [sent, setSent] = useState(false)

  // Signing in keeps out spam; the question itself still isn't linked to the asker
  const handleOpenQuestionModal = () => (user ? setOpenQuestionModal(true) : openLogin())
  const handleCloseQuestionModal = () => setOpenQuestionModal(false)

  const handleSent = () => {
    setOpenQuestionModal(false)
    setSent(true)
  }

  return (
    <>
      <Paper sx={{ p: 3 }}>
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          alignItems="center"
          justifyContent="space-between"
          spacing={2}
        >
          <Typography variant="h6" noWrap sx={{ minWidth: 0, maxWidth: '100%' }}>
            Questions for Bro. Deept4ought? Send anonymously and he will get back to you
          </Typography>
          <Button variant="contained" onClick={handleOpenQuestionModal} sx={{ flexShrink: 0, whiteSpace: 'nowrap' }}>
            Ask Question
          </Button>
        </Stack>
      </Paper>
      <Modal open={openQuestionModal} handleCloseModal={handleCloseQuestionModal}>
        <QuestionForm onSent={handleSent} />
      </Modal>
      <Snackbar open={sent} autoHideDuration={6000} onClose={() => setSent(false)}>
        <Alert severity="success" onClose={() => setSent(false)} variant="filled">
          Your question was sent anonymously.
        </Alert>
      </Snackbar>
    </>
  )
}

export default QuestionsPrompt
