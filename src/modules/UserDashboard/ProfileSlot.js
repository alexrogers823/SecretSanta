import { Box as MuiBox, Typography } from '@mui/material';
import React from 'react';
import { getFullName } from '../../utils/userHelpers';

const ProfileSlot = ({ user }) => {
  if (user.profile_picture_url) {
    return (
      <MuiBox
        component="img"
        src={user.profile_picture_url}
        alt={getFullName(user)}
        sx={{
          display: 'block',
          width: 96,
          height: 96,
          objectFit: 'cover',
          borderRadius: '50%',
          border: '3px solid',
          borderColor: 'common.white',
          boxShadow: 2,
        }}
      />
    )
  }

  return <Typography variant="h5" sx={{ fontWeight: 700 }}>{getFullName(user)}</Typography>
}

export default ProfileSlot
