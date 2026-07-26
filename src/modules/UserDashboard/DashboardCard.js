import { Paper, Stack, Typography } from '@mui/material';
import React from 'react';
import { Button } from '../../common';

const DashboardCard = ({ title, fields = [], emptyMessage, actionLabel, onAction }) => {
  return (
    <Paper sx={{ p: 2, height: '100%' }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
        <Typography variant="h6" gutterBottom>{title}</Typography>
        {actionLabel && <Button size="small" onClick={onAction}>{actionLabel}</Button>}
      </Stack>
      <Stack spacing={1}>
        {fields.length > 0
          ? fields.map((field, index) => (
            <Typography key={index} variant="body2">
              <strong>{field.label}:</strong> {field.value}
            </Typography>
          ))
          : <Typography variant="body2" color="text.secondary">{emptyMessage}</Typography>
        }
      </Stack>
    </Paper>
  )
}

export default DashboardCard
