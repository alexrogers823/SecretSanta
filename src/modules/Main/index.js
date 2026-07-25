import Container from '@mui/material/Container';
import { isEmpty } from 'lodash';
import React, { useEffect, useState } from "react";
import { Box, Button, Modal } from '../../common';
import { Countdown, LoginForm, QuestionForm, SignupForm, XmasForm } from '../../components';

const Main = () => {
  const [message, setMessage] = useState({})
  const [counter, setCounter] = useState(0)
  const [openLogin, setOpenLogin] = useState(false)
  const [openSignup, setOpenSignup] = useState(false)
  const [openGiftsModal, setOpenGiftsModal] = useState(false)
  const [openQuestionModal, setOpenQuestionModal] = useState(false)
  const [data, setData] = useState({ name: "Kevin", giftData: {} })
  const [loggedInName, setLoggedInName] = useState(null)

  const handleOpenLogin = () => {
    setOpenLogin(true)
  }

  const handleCloseLogin = () => {
    setOpenLogin(false)
  }

  const handleLoginSuccess = name => {
    setLoggedInName(name)
    handleCloseLogin()
  }

  const handleOpenSignup = () => {
    setOpenSignup(true)
  }

  const handleCloseSignup = () => {
    setOpenSignup(false)
  }

  const handleSignupSuccess = name => {
    setLoggedInName(name)
    handleCloseSignup()
  }

  const handleOpenGiftsModal = () => {
    setOpenGiftsModal(true)
  }

  const handleCloseGiftsModal = () => {
    setOpenGiftsModal(false)
  }

  const handleOpenQuestionModal = () => {
    setOpenQuestionModal(true)
  }

  const handleCloseQuestionModal = () => {
    setOpenQuestionModal(false)
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

  useEffect(() => {
    const intervalId = setInterval(() => {
      setCounter(time => time + 1)
    }, 1000)

    return () => clearInterval(intervalId)
  }, [])

  return (
    <>
      <Container maxWidth="sm">
        <p>{loggedInName ? `Welcome to Secret Santa, ${loggedInName}!` : "Welcome to Secret Santa!"}</p>
        <Box title={"Signup or login to start adding your desired gifts and other information"} />
        <Button onClick={handleOpenLogin}>Log In</Button>
        <Button onClick={handleOpenSignup}>Sign Up</Button>
        {counter < 40 
          ? <Box title={"Come back after November 27th at 12pm EST to see you're assigned to"} />
          : <Box title={"Click here to review who you're assigned to"} />
        }
        {isEmpty(data.giftData) 
          ? <Box title={`${data.name}, you haven't added your desired gifts yet! Let's do that now`} />
          : <Box title={"Review your information here before Santa comes through"} />
        }
        <Button onClick={handleOpenGiftsModal}>Add Gifts</Button>
        <Box title={"Questions for Bro. Deept4ought? Send anonymously and he will get back to you"} />
        <Button onClick={handleOpenQuestionModal}>Ask Question</Button>
        <Countdown counter={counter} />
      </Container>
      <Modal open={openGiftsModal} handleCloseModal={handleCloseGiftsModal}>
        <XmasForm />
      </Modal>
      <Modal open={openQuestionModal} handleCloseModal={handleCloseQuestionModal}>
        <QuestionForm />
      </Modal>
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