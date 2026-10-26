import { Box as MuiBox } from '@mui/material';
import React from 'react';
import { themeImageUrl } from '../../utils/assets';

const OLD_GOLD = '#cfb53b'
const BLACK = '#000000'

const ChristmasTree = () => {
  return (
    <MuiBox
      sx={{
        maxWidth: 280,
        mx: 'auto',
        p: 1,
        bgcolor: OLD_GOLD,
        border: `3px solid ${BLACK}`,
        borderRadius: 1,
      }}
    >
      <MuiBox
        component="img"
        src={themeImageUrl('christmas-tree.webp')}
        alt="Christmas tree decorated in old gold and black Alpha Phi Alpha ornaments"
        sx={{
          display: 'block',
          width: '100%',
          height: 'auto',
          border: `2px solid ${BLACK}`,
        }}
      />
    </MuiBox>
  )
}

export default ChristmasTree
