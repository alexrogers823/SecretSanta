import { Box as MuiBox, Paper, Stack, Typography } from '@mui/material';
import React from 'react';
import { Button } from '../../common';

const getGradientSx = gradient => {
  if (!gradient) return {}

  const endColor = gradient === 'primary' ? 'secondary' : 'primary'

  return {
    background: theme => `linear-gradient(135deg, ${theme.palette[gradient].main}, ${theme.palette[endColor].main})`,
    color: 'common.white',
    fontWeight: 600,
    textShadow: '0 1px 2px rgba(0, 0, 0, 0.35)',
    '& .MuiTypography-root': { fontWeight: 'inherit' },
    '& a': { color: 'inherit', fontWeight: 700 },
  }
}

const DashboardCard = ({ title, icon, gradient, media, fields = [], emptyMessage, actionLabel, onAction }) => {
  return (
    <Paper sx={{ p: 2, height: '100%', ...getGradientSx(gradient) }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
        <Stack direction="row" alignItems="center" spacing={1}>
          {icon && gradient
            ? <MuiBox sx={{ display: 'flex', p: 0.5, borderRadius: '50%', bgcolor: 'common.white' }}>{icon}</MuiBox>
            : icon}
          <Typography variant="h6" gutterBottom>{title}</Typography>
        </Stack>
        {actionLabel && <Button size="small" color={gradient ? "inherit" : "primary"} onClick={onAction}>{actionLabel}</Button>}
      </Stack>
      {media && <MuiBox sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>{media}</MuiBox>}
      <Stack spacing={1}>
        {fields.length > 0
          ? fields.map((field, index) => (
            <Typography key={index} variant="body2">
              <strong>{field.label}:</strong>{' '}
              {field.url
                ? <a href={field.url} target="_blank" rel="noopener noreferrer">{field.value}</a>
                : field.value}
            </Typography>
          ))
          : <Typography variant="body2" color={gradient ? "inherit" : "text.secondary"}>{emptyMessage}</Typography>
        }
      </Stack>
    </Paper>
  )
}

export default DashboardCard
