import Container from '@mui/material/Container'
import { Paper, Stack, Typography } from '@mui/material'
import { useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import { Button, Modal } from '../../common'
import { isAdmin, useAuth } from '../../context/AuthContext'
import EditUserForm from './EditUserForm'
import QuestionsSection from './QuestionsSection'
import UserTable from './UserTable'

const EMPTY_USER = { id: null, name: '', email: '', address: '' }

const AdminPage = () => {
  const { user } = useAuth()
  const [users, setUsers] = useState([])
  const [editingUser, setEditingUser] = useState(null)
  const [deletingUser, setDeletingUser] = useState(null)
  const [confirmingRegenerate, setConfirmingRegenerate] = useState(false)
  const [regenerateError, setRegenerateError] = useState("")

  useEffect(() => {
    if (!isAdmin(user)) return

    const fetchUsersAndGifts = async () => {
      try {
        const [usersResponse, matchesResponse] = await Promise.all([
          fetch('http://localhost:8000/api/users'),
          fetch('http://localhost:8000/api/matches'),
        ])
        if (!usersResponse.ok) return
        const fetchedUsers = await usersResponse.json()
        const matches = matchesResponse.ok ? await matchesResponse.json() : []
        const assignedToByUserId = Object.fromEntries(
          matches.map(match => [match.user_id, match.assigned_to])
        )

        const usersWithGifts = await Promise.all(
          fetchedUsers.map(async fetchedUser => {
            try {
              const giftsResponse = await fetch(`http://localhost:8000/api/users/${fetchedUser.id}/gifts`)
              const gifts = giftsResponse.ok ? await giftsResponse.json() : []
              return { ...fetchedUser, gifts, assignedTo: assignedToByUserId[fetchedUser.id] || null }
            } catch (error) {
              console.error('Error fetching gifts:', error)
              return { ...fetchedUser, gifts: [], assignedTo: assignedToByUserId[fetchedUser.id] || null }
            }
          })
        )

        setUsers(usersWithGifts)
      } catch (error) {
        console.error('Error fetching users:', error)
      }
    }

    fetchUsersAndGifts()
  }, [user])

  if (!isAdmin(user)) {
    return <Navigate to="/" replace />
  }

  const handleEditSuccess = updatedUser => {
    setUsers(current => current.map(existing => (
      existing.id === updatedUser.id ? { ...existing, ...updatedUser } : existing
    )))
    setEditingUser(null)
  }

  const handleConfirmDelete = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/users/${deletingUser.id}`, {
        method: "DELETE",
      })
      if (response.ok) {
        setUsers(current => current.filter(existing => existing.id !== deletingUser.id))
      }
    } catch (error) {
      console.error('Error deleting user:', error)
    } finally {
      setDeletingUser(null)
    }
  }

  const handleConfirmRegenerate = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/matches/regenerate', { method: "POST" })
      const data = await response.json()

      if (!response.ok) {
        setRegenerateError(data.error || "Unable to regenerate matches.")
        return
      }

      const assignedToByUserId = Object.fromEntries(
        data.map(match => [match.user_id, match.assigned_to])
      )
      setUsers(current => current.map(existing => (
        { ...existing, assignedTo: assignedToByUserId[existing.id] || null }
      )))
      setRegenerateError("")
      setConfirmingRegenerate(false)
    } catch (error) {
      console.error('Error regenerating matches:', error)
      setRegenerateError("Something went wrong. Please try again.")
    }
  }

  return (
    <>
      <Container maxWidth="md" sx={{ mt: 2 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="h5" gutterBottom>Admin</Typography>
          <Button
            size="small"
            disabled={users.length < 2}
            title={users.length < 2 ? "At least 2 users are required to generate matches" : undefined}
            onClick={() => setConfirmingRegenerate(true)}
          >
            Regenerate Matches
          </Button>
        </Stack>
        <UserTable
          users={users}
          onEdit={setEditingUser}
          onDelete={setDeletingUser}
          currentAdminEmail={user.email}
        />
        <QuestionsSection />
      </Container>
      <Modal open={!!editingUser} handleCloseModal={() => setEditingUser(null)}>
        <EditUserForm
          key={editingUser?.id ?? 'none'}
          user={editingUser || EMPTY_USER}
          onEditSuccess={handleEditSuccess}
        />
      </Modal>
      <Modal open={!!deletingUser} handleCloseModal={() => setDeletingUser(null)}>
        <Paper sx={{ p: 2, maxWidth: 400, mx: "auto", mt: "20vh" }}>
          <Typography variant="h6" gutterBottom>Delete User</Typography>
          <Typography variant="body2" gutterBottom>
            {`Are you sure you want to delete ${deletingUser?.name}? This cannot be undone.`}
          </Typography>
          <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
            <Button onClick={() => setDeletingUser(null)}>Cancel</Button>
            <Button color="error" onClick={handleConfirmDelete}>Delete</Button>
          </Stack>
        </Paper>
      </Modal>
      <Modal
        open={confirmingRegenerate}
        handleCloseModal={() => { setConfirmingRegenerate(false); setRegenerateError("") }}
      >
        <Paper sx={{ p: 2, maxWidth: 400, mx: "auto", mt: "20vh" }}>
          <Typography variant="h6" gutterBottom>Regenerate Matches</Typography>
          <Typography variant="body2" gutterBottom>
            Are you sure you want to regenerate matches? This will reshuffle everyone's assignment and cannot be undone.
          </Typography>
          {regenerateError && (
            <Typography variant="body2" color="error" gutterBottom>{regenerateError}</Typography>
          )}
          <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
            <Button onClick={() => { setConfirmingRegenerate(false); setRegenerateError("") }}>Cancel</Button>
            <Button color="error" onClick={handleConfirmRegenerate}>Regenerate</Button>
          </Stack>
        </Paper>
      </Modal>
    </>
  )
}

export default AdminPage
