import Container from '@mui/material/Container'
import { Paper, Stack, Typography } from '@mui/material'
import { useEffect, useState } from "react"
import { Navigate } from "react-router-dom"
import { apiFetch, getErrorMessage } from '../../api/client'
import { Button, Modal } from '../../common'
import { isAdmin, useAuth } from '../../context/AuthContext'
import { getFullName } from '../../utils/userHelpers'
import EditUserForm from './EditUserForm'
import QuestionsSection from './QuestionsSection'
import UserTable from './UserTable'

const EMPTY_USER = { id: null, first_name: '', last_name: '', email: '', address: '' }

const AdminPage = () => {
  const { user, loading } = useAuth()
  const [users, setUsers] = useState([])
  const [editingUser, setEditingUser] = useState(null)
  const [deletingUser, setDeletingUser] = useState(null)
  const [confirmingRegenerate, setConfirmingRegenerate] = useState(false)
  const [regenerateError, setRegenerateError] = useState("")
  const [notice, setNotice] = useState("")

  useEffect(() => {
    if (!isAdmin(user)) return

    const fetchOverview = async () => {
      try {
        // Users with their gifts, matches and photo counts, in one call
        const overview = await apiFetch('/api/admin/overview')
        setUsers(overview.users)
      } catch (error) {
        console.error('Error fetching users:', error)
      }
    }

    fetchOverview()
  }, [user])

  if (loading) return null
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
      const data = await apiFetch(`/api/users/${deletingUser.id}`, { method: "DELETE" })
      setUsers(current => current.filter(existing => existing.id !== deletingUser.id))
      // Set when matches were already drawn: someone has lost their match until you regenerate
      setNotice(data.warning || "")
    } catch (error) {
      console.error('Error deleting user:', error)
    } finally {
      setDeletingUser(null)
    }
  }

  const handleConfirmRegenerate = async () => {
    try {
      const matches = await apiFetch('/api/matches/regenerate', { method: "POST" })
      const assignedToByUserId = Object.fromEntries(
        matches.map(match => [match.user_id, match.assigned_to])
      )
      setUsers(current => current.map(existing => (
        { ...existing, assigned_to: assignedToByUserId[existing.id] || null }
      )))
      setRegenerateError("")
      setNotice("")
      setConfirmingRegenerate(false)
    } catch (error) {
      console.error('Error regenerating matches:', error)
      setRegenerateError(getErrorMessage(error, "Unable to regenerate matches."))
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
        {notice && <Typography variant="body2" color="error" gutterBottom>{notice}</Typography>}
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
            {`Are you sure you want to delete ${getFullName(deletingUser)}? This cannot be undone.`}
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
