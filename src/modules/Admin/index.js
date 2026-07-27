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

  useEffect(() => {
    if (!isAdmin(user)) return

    const fetchUsersAndGifts = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/users')
        if (!response.ok) return
        const fetchedUsers = await response.json()

        const usersWithGifts = await Promise.all(
          fetchedUsers.map(async fetchedUser => {
            try {
              const giftsResponse = await fetch(`http://localhost:8000/api/users/${fetchedUser.id}/gifts`)
              const gifts = giftsResponse.ok ? await giftsResponse.json() : []
              return { ...fetchedUser, gifts }
            } catch (error) {
              console.error('Error fetching gifts:', error)
              return { ...fetchedUser, gifts: [] }
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

  return (
    <>
      <Container maxWidth="md" sx={{ mt: 2 }}>
        <Typography variant="h5" gutterBottom>Admin</Typography>
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
    </>
  )
}

export default AdminPage
