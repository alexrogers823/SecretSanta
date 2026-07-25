import Container from '@mui/material/Container';
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Modal } from '../../common';
import { LoginForm, SignupForm } from '../../components';
import { useAuth } from '../../context/AuthContext';

const Main = () => {
  const [message, setMessage] = useState({})
  const [openLogin, setOpenLogin] = useState(false)
  const [openSignup, setOpenSignup] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleOpenLogin = () => {
    setOpenLogin(true)
  }

  const handleCloseLogin = () => {
    setOpenLogin(false)
  }

  const handleLoginSuccess = user => {
    login(user)
    handleCloseLogin()
    navigate(`/dashboard/${user.id}`)
  }

  const handleOpenSignup = () => {
    setOpenSignup(true)
  }

  const handleCloseSignup = () => {
    setOpenSignup(false)
  }

  const handleSignupSuccess = user => {
    login(user)
    handleCloseSignup()
    navigate(`/dashboard/${user.id}`)
  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("http://localhost:8000/api")
        if (!response.ok) {
          throw new Error('Network response failed');
        }
        const jsonData = await response.json();
        setMessage(jsonData);
      } catch (error) {
        console.error('Error fetching data:', error)
      }
    }

    fetchData();
  }, []);

  return (
    <>
      <Container maxWidth="sm">
        <p>Welcome to Secret Santa!</p>
        <Box title={"Signup or login to start adding your desired gifts and other information"} />
        <Button onClick={handleOpenLogin}>Log In</Button>
        <Button onClick={handleOpenSignup}>Sign Up</Button>
      </Container>
      <Modal open={openLogin} handleCloseModal={handleCloseLogin}>
        <LoginForm onLoginSuccess={handleLoginSuccess} />
      </Modal>
      <Modal open={openSignup} handleCloseModal={handleCloseSignup}>
        <SignupForm onSignupSuccess={handleSignupSuccess} />
      </Modal>
    </>
  )
}

export default Main
