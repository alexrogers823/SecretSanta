import { createTheme } from '@mui/material';

// Christmas Color Palette: https://www.color-hex.com/color-palette/1483
const theme = createTheme({
  palette: {
    primary: {
      main: '#378b29',
      light: '#74d680',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#ff0000',
      light: '#ff7878',
      contrastText: '#ffffff',
    },
    background: {
      default: '#ffffff',
      paper: '#ffffff',
    },
  },
})

export default theme
