import { Grid } from '@mui/material';
import Container from '@mui/material/Container';
import React, { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import { Box, Button, Modal } from '../../common';
import { Countdown, EditProfileForm, GIFT_OPTIONS, QuestionForm, XmasForm } from '../../components';
import { useAuth } from '../../context/AuthContext';
import DashboardCard from './DashboardCard';

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
  const [assigneeData, setAssigneeData] = useState(null)
  const [assigneeGifts, setAssigneeGifts] = useState([])
  const [assigneeError, setAssigneeError] = useState("")
  const hasRequestedMatch = useRef(false)

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

  useEffect(() => {
    if (counter < 40 || !user?.id || hasRequestedMatch.current) return
    hasRequestedMatch.current = true
    let cancelled = false

    const revealMatch = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/matches/generate', { method: "POST" })
        const data = await response.json()

        if (!response.ok) {
          if (!cancelled) setAssigneeError(data.error || "Unable to reveal your assignment yet.")
          return
        }

        const mine = data.find(match => match.user_id === user.id)
        if (cancelled || !mine?.assigned_to) return

        setAssigneeData(mine.assigned_to)

        const giftsResponse = await fetch(`http://localhost:8000/api/users/${mine.assigned_to.id}/gifts`)
        if (giftsResponse.ok && !cancelled) {
          setAssigneeGifts(await giftsResponse.json())
        }
      } catch (error) {
        console.error('Error revealing assignment:', error)
        if (!cancelled) setAssigneeError("Something went wrong. Please try again.")
      }
    }

    revealMatch()
    return () => { cancelled = true }
  }, [counter, user?.id])

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

  const assigneeGiftFields = assigneeGifts
    .map(gift => [
      { label: "Gift", value: gift.name, url: gift.url || undefined },
      { label: "Notes", value: gift.notes || "—" },
    ])
    .flat()

  const assigneeEmptyMessage = assignmentRevealed
    ? (assigneeError || "Fetching your assignment...")
    : "Come back after November 25th at 12pm EST to see who you're assigned to"

  const assigneeGiftsEmptyMessage = assignmentRevealed && assigneeData
    ? `${assigneeData.name} hasn't added their desired gifts yet`
    : assigneeEmptyMessage

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
              fields={assignmentRevealed && assigneeData
                ? [
                  { label: "Name", value: assigneeData.name },
                  { label: "Address", value: assigneeData.address },
                ]
                : []
              }
              emptyMessage={assigneeEmptyMessage}
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
              fields={assignmentRevealed && assigneeData ? assigneeGiftFields : []}
              emptyMessage={assigneeGiftsEmptyMessage}
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
        <XmasForm initialValues={giftData} onSubmit={handleGiftsSubmit} error={giftsError} userName={user.name} />
      </Modal>
      <Modal open={openQuestionModal} handleCloseModal={handleCloseQuestionModal}>
        <QuestionForm />
      </Modal>
    </>
  )
}

export default UserDashboard
