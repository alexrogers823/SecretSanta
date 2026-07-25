import Container from '@mui/material/Container';
import { isEmpty } from 'lodash';
import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Box, Button, Modal } from '../../common';
import { Countdown, QuestionForm, XmasForm } from '../../components';
import { useAuth } from '../../context/AuthContext';

const UserDashboard = () => {
  const { user } = useAuth()
  const [counter, setCounter] = useState(0)
  const [openGiftsModal, setOpenGiftsModal] = useState(false)
  const [openQuestionModal, setOpenQuestionModal] = useState(false)
  const [data, setData] = useState({ giftData: {} })

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
    const intervalId = setInterval(() => {
      setCounter(time => time + 1)
    }, 1000)

    return () => clearInterval(intervalId)
  }, [])

  if (!user) {
    return <Navigate to="/" replace />
  }

  return (
    <>
      <Container maxWidth="sm">
        <p>{`Welcome back, ${user.name}!`}</p>
        {counter < 40
          ? <Box title={"Come back after November 27th at 12pm EST to see you're assigned to"} />
          : <Box title={"Click here to review who you're assigned to"} />
        }
        {isEmpty(data.giftData)
          ? (
            <>
              <Box title={`${user.name}, you haven't added your desired gifts yet! Let's do that now`} />
              <Button onClick={handleOpenGiftsModal}>Add Gifts</Button>
            </>
          )
          : <Box title={"Review your information here before Santa comes through"} />
        }
        <Box title={"Questions for Bro. Deept4ought? Send anonymously and he will get back to you"} />
        <Button onClick={handleOpenQuestionModal}>Ask Question</Button>
        <Countdown counter={counter} />
      </Container>
      {isEmpty(data.giftData) && (
        <Modal open={openGiftsModal} handleCloseModal={handleCloseGiftsModal}>
          <XmasForm />
        </Modal>
      )}
      <Modal open={openQuestionModal} handleCloseModal={handleCloseQuestionModal}>
        <QuestionForm />
      </Modal>
    </>
  )
}

export default UserDashboard
