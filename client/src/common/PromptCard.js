import { Paper, Typography } from '@mui/material';
import React from 'react';

const PromptCard = ({ message, children }) => {
  return (
    <Paper sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
      <Typography variant="h6" gutterBottom>{message}</Typography>
      {children}
    </Paper>
  )
}

export default PromptCard
