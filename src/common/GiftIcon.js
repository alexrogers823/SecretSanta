import { SvgIcon, useTheme } from '@mui/material';
import React from 'react';

const GiftIcon = ({ boxColor = 'primary', ribbonColor = 'secondary', ...rest }) => {
  const theme = useTheme()
  const boxFill = theme.palette[boxColor].main
  const ribbonFill = theme.palette[ribbonColor].main

  return (
    <SvgIcon {...rest}>
      <rect x="3" y="7" width="18" height="4" rx="1" fill={boxFill} />
      <rect x="4" y="11" width="16" height="10" rx="1" fill={boxFill} />
      <rect x="10.5" y="7" width="3" height="14" fill={ribbonFill} />
      <path d="M12 7C9.5 2.5 5 3.5 7.5 7Z" fill={ribbonFill} />
      <path d="M12 7C14.5 2.5 19 3.5 16.5 7Z" fill={ribbonFill} />
    </SvgIcon>
  )
}

export default GiftIcon
