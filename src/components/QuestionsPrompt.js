import { Paper, Stack, Typography } from '@mui/material';
import React, { useState } from 'react';
import { Button, Modal } from '../common';
import QuestionForm from './QuestionForm';

const QuestionsPrompt = () => {
  const [openQuestionModal, setOpenQuestionModal] = useState(false)

  const handleOpenQuestionModal = () => setOpenQuestionModal(true)
  const handleCloseQuestionModal = () => setOpenQuestionModal(false)

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
        <QuestionForm />
      </Modal>
    </>
  )
}

export default QuestionsPrompt
