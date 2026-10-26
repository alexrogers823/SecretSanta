import MenuIcon from '@mui/icons-material/Menu';
import { AppBar, IconButton, Menu, MenuItem, Box as MuiBox, Stack, Toolbar, Typography } from '@mui/material';
import React, { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { isAdmin, useAuth } from '../context/AuthContext';
import { useAuthModal } from '../context/AuthModalContext';
import useMatch from '../hooks/useMatch';
import { getNextChristmasDate, getNextMatchDate } from '../utils/dateHelpers';
import Button from './Button';
import CountdownTimer from './CountdownTimer';

const Header = () => {
  const { user, logout } = useAuth()
  const { openLogin, openSignup } = useAuthModal()
  const { match } = useMatch()
  const navigate = useNavigate()

  // Signed in, count down to the server's reveal time (the one that actually unlocks matches);
  // signed out, or once revealed, fall back to the next Nov 25th at 12pm EST
  const revealAt = match && !match.revealed ? match.reveal_at : null
  const getMatchDate = useCallback(() => (revealAt ? new Date(revealAt) : getNextMatchDate()), [revealAt])
  const [anchorEl, setAnchorEl] = useState(null)

  const handleOpenMenu = event => setAnchorEl(event.currentTarget)
  const handleCloseMenu = () => setAnchorEl(null)

  const handleNavigateHome = () => {
    handleCloseMenu()
    navigate('/')
  }

  const handleNavigateDashboard = () => {
    handleCloseMenu()
    navigate(`/dashboard/${user.id}`)
  }

  const handleNavigateAdmin = () => {
    handleCloseMenu()
    navigate('/admin')
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <>
      <AppBar position="static">
        <Toolbar sx={{ justifyContent: 'space-between', flexWrap: 'wrap', columnGap: 2 }}>
          <Typography
            variant="h6"
            noWrap
            onClick={() => navigate('/')}
            sx={{ cursor: 'pointer', fontSize: { xs: '1.1rem', sm: '1.25rem' } }}
          >
            Secret Santa X
          </Typography>
          <Stack
            direction={{ xs: 'row', sm: 'column', md: 'row' }}
            justifyContent="center"
            alignItems="center"
            columnGap={{ xs: 2, md: 4, lg: 8 }}
            sx={{ order: { xs: 1, sm: 0 }, width: { xs: '100%', sm: 'auto' }, pb: { xs: 1, sm: 0 } }}
          >
            <CountdownTimer label="Countdown to Your Match" shortLabel="Match" getTargetDate={getMatchDate} />
            <CountdownTimer label="Countdown to Christmas" shortLabel="Christmas" getTargetDate={getNextChristmasDate} />
          </Stack>
          {user ? (
            <Typography component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography component="span" noWrap sx={{ display: { xs: 'none', sm: 'block' } }}>
                <MuiBox component="span" sx={{ display: { xs: 'none', lg: 'inline' } }}>Logged In as </MuiBox>
                {user.first_name}
              </Typography>
              <IconButton color="inherit" onClick={handleOpenMenu}>
                <MenuIcon />
              </IconButton>
              <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleCloseMenu}>
                <MenuItem onClick={handleNavigateHome}>Home</MenuItem>
                <MenuItem onClick={handleNavigateDashboard}>Dashboard</MenuItem>
                {isAdmin(user) && <MenuItem onClick={handleNavigateAdmin}>Admin Page</MenuItem>}
              </Menu>
              <Button onClick={handleLogout} color="inherit" sx={{ whiteSpace: 'nowrap' }}>Log Out</Button>
            </Typography>
          ) : (
            <Typography component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Button onClick={openLogin} color="inherit" sx={{ whiteSpace: 'nowrap' }}>Log In</Button>
              <Button onClick={openSignup} color="inherit" sx={{ whiteSpace: 'nowrap' }}>Sign Up</Button>
            </Typography>
          )}
        </Toolbar>
      </AppBar>
    </>
  )
}

export default Header
