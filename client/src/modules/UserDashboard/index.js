import { Grid, Box as MuiBox, Stack } from '@mui/material';
import Container from '@mui/material/Container';
import React, { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { apiFetch, getErrorMessage } from '../../api/client';
import { GiftIcon, Modal } from '../../common';
import { EditProfileForm, GIFT_OPTIONS, PhotoGallery, XmasForm } from '../../components';
import { useAuth } from '../../context/AuthContext';
import useMatch from '../../hooks/useMatch';
import { getFullName } from '../../utils/userHelpers';
import DashboardCard from './DashboardCard';
import Ornament from './Ornament';
import ProfileSlot from './ProfileSlot';

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
  const { user, loading, updateUser } = useAuth()
  const [openProfileModal, setOpenProfileModal] = useState(false)
  const [openGiftsModal, setOpenGiftsModal] = useState(false)
  const [giftData, setGiftData] = useState({})
  const [giftsError, setGiftsError] = useState("")
  // {revealed, reveal_at, receiver, gifts} from /api/matches/me; null until it loads
  const { match, error: assigneeError } = useMatch()

  const handleOpenProfileModal = () => { setOpenProfileModal(true) }
  const handleCloseProfileModal = () => { setOpenProfileModal(false) }
  const handleOpenGiftsModal = () => { setOpenGiftsModal(true) }
  const handleCloseGiftsModal = () => { setOpenGiftsModal(false) }

  const handleEditProfileSuccess = updatedUser => {
    updateUser(updatedUser)
    handleCloseProfileModal()
  }

  const handleGiftsSubmit = async collected => {
    const gifts = flatGiftsToPayload(collected)
    try {
      const savedGifts = await apiFetch("/api/me/gifts", { method: "PUT", body: { gifts } })
      setGiftsError("")
      setGiftData(giftsResponseToFlat(savedGifts))
      handleCloseGiftsModal()
    } catch (error) {
      console.error('Error saving gifts:', error)
      setGiftsError(getErrorMessage(error))
    }
  }

  useEffect(() => {
    if (!user?.id) return

    const fetchGifts = async () => {
      try {
        setGiftData(giftsResponseToFlat(await apiFetch("/api/me/gifts")))
      } catch (error) {
        console.error('Error fetching gifts:', error)
      }
    }

    fetchGifts()
  }, [user?.id])

  // Wait for Firebase to restore the session before deciding the user is signed out
  if (loading) return null
  if (!user) {
    return <Navigate to="/" replace />
  }

  const assignmentRevealed = !!match?.revealed
  const assigneeData = match?.receiver || null
  const assigneeGifts = match?.gifts || []

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

  const assigneeEmptyMessage = assigneeError
    || (!match && "Checking for your assignment...")
    // Revealed but no receiver: they left after the draw, and matches are being redrawn
    || (assignmentRevealed && "Your assignment is being updated. Check back soon.")
    || "Come back after November 25th at 12pm EST to see who you're assigned to"

  const assigneeGiftsEmptyMessage = assignmentRevealed && assigneeData
    ? `${assigneeData.first_name} hasn't added their desired gifts yet`
    : assigneeEmptyMessage

  return (
    <>
      <Container maxWidth="lg" sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <p>{`Welcome back, ${user.first_name}!`}</p>
        <Stack justifyContent="center" sx={{ flex: 1 }}>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={4}>
              <Stack spacing={3}>
                <DashboardCard
                  title="Your Information"
                  gradient="primary"
                  media={<ProfileSlot user={user} />}
                  fields={[
                    { label: "Address", value: user.address },
                    { label: "Email", value: user.email },
                  ]}
                  actionLabel="Edit"
                  onAction={handleOpenProfileModal}
                />
                <DashboardCard
                  title="Your Desired Gifts"
                  gradient="primary"
                  icon={<GiftIcon boxColor="primary" ribbonColor="secondary" />}
                  fields={giftFields}
                  emptyMessage={`${user.first_name}, you haven't added your desired gifts yet! Let's do that now`}
                  actionLabel={giftFields.length > 0 ? "Edit" : "Add"}
                  onAction={handleOpenGiftsModal}
                />
              </Stack>
            </Grid>
            <Grid item xs={12} md={4}>
              <Ornament />
            </Grid>
            <Grid item xs={12} md={4}>
              <Stack spacing={3}>
                <DashboardCard
                  title="Your Chosen LB's Information"
                  gradient="secondary"
                  media={assignmentRevealed && assigneeData ? <ProfileSlot user={assigneeData} /> : null}
                  fields={assignmentRevealed && assigneeData
                    ? [
                      // Without a picture, ProfileSlot already shows the full name
                      ...(assigneeData.profile_picture_url ? [{ label: "Name", value: getFullName(assigneeData) }] : []),
                      { label: "Address", value: assigneeData.address },
                    ]
                    : []
                  }
                  emptyMessage={assigneeEmptyMessage}
                />
                <DashboardCard
                  title="His Desired Gifts"
                  gradient="secondary"
                  icon={<GiftIcon boxColor="secondary" ribbonColor="primary" />}
                  fields={assignmentRevealed && assigneeData ? assigneeGiftFields : []}
                  emptyMessage={assigneeGiftsEmptyMessage}
                />
              </Stack>
            </Grid>
          </Grid>
        </Stack>
        <MuiBox sx={{ mt: 4 }}>
          <PhotoGallery />
        </MuiBox>
      </Container>
      <Modal open={openProfileModal} handleCloseModal={handleCloseProfileModal}>
        <EditProfileForm user={user} onEditSuccess={handleEditProfileSuccess} />
      </Modal>
      <Modal open={openGiftsModal} handleCloseModal={handleCloseGiftsModal}>
        <XmasForm initialValues={giftData} onSubmit={handleGiftsSubmit} error={giftsError} userName={getFullName(user)} />
      </Modal>
    </>
  )
}

export default UserDashboard
