import { Button as MuiButton } from '@mui/material';
import React from 'react';

const Button = props => {
  return <MuiButton onClick={props.onClick} variant={props.variant || "outlined"} {...props}>{props.children}</MuiButton>
}

export default Button