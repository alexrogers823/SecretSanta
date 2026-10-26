import { Box as MuiBox } from '@mui/material';
import React from 'react';
import { themeImageUrl } from '../../utils/assets';

const Ornament = () => {
  return (
    <MuiBox
      component="img"
      src={themeImageUrl('ornament.webp')}
      alt="Alpha Phi Alpha Fraternity, Inc. 1906 Christmas ornament"
      sx={{
        display: 'block',
        width: '100%',
        maxWidth: 280,
        height: 'auto',
        mx: 'auto',
        filter: 'drop-shadow(0 6px 12px rgba(0, 0, 0, 0.35))',
      }}
    />
  )
}

export default Ornament
