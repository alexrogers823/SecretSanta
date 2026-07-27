import { Grid } from '@mui/material';
import Container from '@mui/material/Container';
import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Box, Button, Modal } from '../../common';
import { Countdown, EditProfileForm, GIFT_OPTIONS, QuestionForm, XmasForm } from '../../components';
import { useAuth } from '../../context/AuthContext';
import DashboardCard from './DashboardCard';

// Placeholder until a real assignee/pairing backend exists.
const MOCK_ASSIGNEE = {
  name: "Jane Doe",
  address: "123 Elf Lane, North Pole",
  gifts: [
    { gift: "Board game", url: "https://www.example.com/board-game", notes: "Strategy, not party games" },
    { gift: "Socks", url: "", notes: "Size 10" },
  ],
}

const flatGiftsToPayload = collected => GIFT_OPTIONS
  .map(option => ({
    name: collected[option.id],
    url: collected[`${option.id}Url`],
    notes: collected[`${option.id}Notes`],
  }))
  .filter(gift => gift.name && gift.name.trim())

const giftsResponseToFlat = gifts => {
  const flat = {}
  gifts.forEach((gift, index) => {
    const option = GIFT_OPTIONS[index]
    if (!option) return
    flat[option.id] = gift.name
    flat[`${option.id}Url`] = gift.url || ""
    flat[`${option.id}Notes`] = gift.notes || ""
  })
  return flat
}

const UserDashboard = () => {
  const { user, login } = useAuth()
  const [counter, setCounter] = useState(0)
  const [openProfileModal, setOpenProfileModal] = useState(false)
  const [openGiftsModal, setOpenGiftsModal] = useState(false)
  const [openQuestionModal, setOpenQuestionModal] = useState(false)
  const [giftData, setGiftData] = useState({})
  const [giftsError, setGiftsError] = useState("")

  const handleOpenProfileModal = () => { setOpenProfileModal(true) }
  const handleCloseProfileModal = () => { setOpenProfileModal(false) }
  const handleOpenGiftsModal = () => { setOpenGiftsModal(true) }
  const handleCloseGiftsModal = () => { setOpenGiftsModal(false) }
  const handleOpenQuestionModal = () => { setOpenQuestionModal(true) }
  const handleCloseQuestionModal = () => { setOpenQuestionModal(false) }

  const handleEditProfileSuccess = updatedUser => {
    login(updatedUser)
    handleCloseProfileModal()
  }

  const handleGiftsSubmit = async collected => {
    const gifts = flatGiftsToPayload(collected)
    try {
      const response = await fetch(`http://localhost:8000/api/users/${user.id}/gifts`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gifts }),
      })
      const data = await response.json()

      if (response.ok) {
        setGiftsError("")
        setGiftData(giftsResponseToFlat(data))
        handleCloseGiftsModal()
      } else {
        setGiftsError(data.error || "Something went wrong. Please try again.")
      }
    } catch (error) {
      console.error('Error saving gifts:', error)
      setGiftsError("Something went wrong. Please try again.")
    }
  }

  useEffect(() => {
    const intervalId = setInterval(() => {
      setCounter(time => time + 1)
    }, 1000)
    return () => clearInterval(intervalId)
  }, [])

  useEffect(() => {
    if (!user?.id) return

    const fetchGifts = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/users/${user.id}/gifts`)
        if (response.ok) {
          setGiftData(giftsResponseToFlat(await response.json()))
        }
      } catch (error) {
        console.error('Error fetching gifts:', error)
      }
    }

    fetchGifts()
  }, [user?.id])

  if (!user) {
    return <Navigate to="/" replace />
  }

  const assignmentRevealed = counter >= 40

  const giftFields = GIFT_OPTIONS
    .filter(option => giftData[option.id])
    .map(option => [
      { label: "Gift", value: giftData[option.id], url: giftData[`${option.id}Url`] || undefined },
      { label: "Notes", value: giftData[`${option.id}Notes`] || "—" },
    ])
    .flat()

  const assigneeGiftFields = MOCK_ASSIGNEE.gifts
    .map(({ gift, url, notes }) => [
      { label: "Gift", value: gift, url: url || undefined },
      { label: "Notes", value: notes },
    ])
    .flat()

  return (
    <>
      <Container maxWidth="md">
        <p>{`Welcome back, ${user.name}!`}</p>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={6}>
            <DashboardCard
              title="Your Information"
              fields={[
                { label: "Address", value: user.address },
                { label: "Email", value: user.email },
              ]}
              actionLabel="Edit"
              onAction={handleOpenProfileModal}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <DashboardCard
              title="Your Chosen LB's Information"
              fields={assignmentRevealed
                ? [
                  { label: "Name", value: MOCK_ASSIGNEE.name },
                  { label: "Address", value: MOCK_ASSIGNEE.address },
                ]
                : []
              }
              emptyMessage="Come back after November 27th at 12pm EST to see who you're assigned to"
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <DashboardCard
              title="Your Desired Gifts"
              fields={giftFields}
              emptyMessage={`${user.name}, you haven't added your desired gifts yet! Let's do that now`}
              actionLabel={giftFields.length > 0 ? "Edit" : "Add"}
              onAction={handleOpenGiftsModal}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <DashboardCard
              title="His Desired Gifts"
              fields={assignmentRevealed ? assigneeGiftFields : []}
              emptyMessage="Assignments haven't been revealed yet"
            />
          </Grid>
        </Grid>
        <Box title={"Questions for Bro. Deept4ought? Send anonymously and he will get back to you"} />
        <Button onClick={handleOpenQuestionModal}>Ask Question</Button>
        <Countdown counter={counter} />
      </Container>
      <Modal open={openProfileModal} handleCloseModal={handleCloseProfileModal}>
        <EditProfileForm user={user} onEditSuccess={handleEditProfileSuccess} />
      </Modal>
      <Modal open={openGiftsModal} handleCloseModal={handleCloseGiftsModal}>
        <XmasForm initialValues={giftData} onSubmit={handleGiftsSubmit} error={giftsError} />
      </Modal>
      <Modal open={openQuestionModal} handleCloseModal={handleCloseQuestionModal}>
        <QuestionForm />
      </Modal>
    </>
  )
}

export default UserDashboard
