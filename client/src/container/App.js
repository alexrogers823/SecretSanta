import { Container, Box as MuiBox, ThemeProvider } from '@mui/material';
import React from 'react';
import {
  Route,
  BrowserRouter as Router,
  Routes
} from "react-router-dom";
import { Header } from '../common';
import { QuestionsPrompt } from '../components';
import { AuthProvider } from '../context/AuthContext';
import { AuthModalProvider } from '../context/AuthModalContext';
import { MatchProvider } from '../hooks/useMatch';
import About from '../modules/About';
import AdminPage from '../modules/Admin';
import Main from '../modules/Main';
import UserDashboard from '../modules/UserDashboard';
import theme from '../theme';
import { themeImageUrl } from '../utils/assets';

const BACKGROUND_OVERLAY = 'rgba(255, 255, 255, 0.55)'
const BACKGROUND_IMAGE = themeImageUrl('background.webp')

const App = () => {
  return (
    <ThemeProvider theme={theme}>
      <Router>
        <AuthProvider>
          <MatchProvider>
            <AuthModalProvider>
              <MuiBox sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
                <Header />
                <MuiBox
                  component="main"
                  sx={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    backgroundImage: `linear-gradient(${BACKGROUND_OVERLAY}, ${BACKGROUND_OVERLAY}), url(${BACKGROUND_IMAGE})`,
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
                  <Container maxWidth="lg" sx={{ py: 4 }}>
                    <QuestionsPrompt />
                  </Container>
                </MuiBox>
              </MuiBox>
            </AuthModalProvider>
          </MatchProvider>
        </AuthProvider>
      </Router>
    </ThemeProvider>
  )
}

export default App