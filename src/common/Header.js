import MenuIcon from '@mui/icons-material/Menu';
import { AppBar, IconButton, Menu, MenuItem, Toolbar, Typography } from '@mui/material';
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LoginForm, SignupForm } from '../components';
import { isAdmin, useAuth } from '../context/AuthContext';
import Button from './Button';
import Modal from './Modal';

const Header = () => {
  const { user, login, logout } = useAuth()
  const navigate = useNavigate()
  const [openLogin, setOpenLogin] = useState(false)
  const [openSignup, setOpenSignup] = useState(false)
  const [anchorEl, setAnchorEl] = useState(null)

  const handleOpenLogin = () => setOpenLogin(true)
  const handleCloseLogin = () => setOpenLogin(false)

  const handleLoginSuccess = loggedInUser => {
    login(loggedInUser)
    handleCloseLogin()
    navigate(`/dashboard/${loggedInUser.id}`)
  }

  const handleOpenSignup = () => setOpenSignup(true)
  const handleCloseSignup = () => setOpenSignup(false)

  const handleSignupSuccess = signedUpUser => {
    login(signedUpUser)
    handleCloseSignup()
    navigate(`/dashboard/${signedUpUser.id}`)
  }

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
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Typography
            variant="h6"
            onClick={() => navigate('/')}
            sx={{ cursor: 'pointer' }}
          >
            Secret Santa X
          </Typography>
          {user ? (
            <Typography component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography component="span">{`Logged In as ${user.name}`}</Typography>
              <IconButton color="inherit" onClick={handleOpenMenu}>
                <MenuIcon />
              </IconButton>
              <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleCloseMenu}>
                <MenuItem onClick={handleNavigateHome}>Home</MenuItem>
                <MenuItem onClick={handleNavigateDashboard}>Dashboard</MenuItem>
                {isAdmin(user) && <MenuItem onClick={handleNavigateAdmin}>Admin Page</MenuItem>}
              </Menu>
              <Button onClick={handleLogout} color="inherit">Log Out</Button>
            </Typography>
          ) : (
            <Typography component="div" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Button onClick={handleOpenLogin} color="inherit">Log In</Button>
              <Button onClick={handleOpenSignup} color="inherit">Sign Up</Button>
            </Typography>
          )}
        </Toolbar>
      </AppBar>
      <Modal open={openLogin} handleCloseModal={handleCloseLogin}>
        <LoginForm onLoginSuccess={handleLoginSuccess} />
      </Modal>
      <Modal open={openSignup} handleCloseModal={handleCloseSignup}>
        <SignupForm onSignupSuccess={handleSignupSuccess} />
      </Modal>
    </>
  )
}

export default Header
