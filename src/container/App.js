import { Box as MuiBox, ThemeProvider } from '@mui/material';
import React from 'react';
import {
  Route,
  BrowserRouter as Router,
  Routes
} from "react-router-dom";
import backgroundImage from '../assets/background.png';
import { Header } from '../common';
import { AuthProvider } from '../context/AuthContext';
import About from '../modules/About';
import AdminPage from '../modules/Admin';
import Main from '../modules/Main';
import UserDashboard from '../modules/UserDashboard';
import theme from '../theme';

const BACKGROUND_OVERLAY = 'rgba(255, 255, 255, 0.55)'

const App = () => {
  return (
    <ThemeProvider theme={theme}>
      <Router>
        <AuthProvider>
          <MuiBox sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <Header />
            <MuiBox
              component="main"
              sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                backgroundImage: `linear-gradient(${BACKGROUND_OVERLAY}, ${BACKGROUND_OVERLAY}), url(${backgroundImage})`,
                backgroundSize: 'cover, contain',
                backgroundPosition: 'center, center bottom',
                backgroundRepeat: 'no-repeat',
              }}
            >
              <Routes>
                <Route path="/about" element={<About />} />
                <Route path="/dashboard/:userId" element={<UserDashboard />} />
                <Route path="/admin" element={<AdminPage />} />
                <Route path="/" element={<Main />} />
              </Routes>
            </MuiBox>
          </MuiBox>
        </AuthProvider>
      </Router>
    </ThemeProvider>
  )
}

export default App