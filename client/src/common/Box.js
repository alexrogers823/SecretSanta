import { Box as MuiBox } from '@mui/material';
import * as React from 'react';

const Box = props => {
  return (
    <MuiBox component="section" sx={{ p: 2, border: '1px dashed grey', bgcolor: 'rgba(255, 255, 255, 0.9)', borderRadius: 1 }}>
      {props.title}
    </MuiBox>
  );
}

export default Box