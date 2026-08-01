import {
  Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow
} from "@mui/material"
import { useState } from "react"
import { Button } from "../../common"

const UserTable = ({ users, onEdit, onDelete, currentAdminEmail }) => {
  const [revealedIds, setRevealedIds] = useState(new Set())

  const toggleRevealed = userId => {
    setRevealedIds(current => {
      const next = new Set(current)
      if (next.has(userId)) {
        next.delete(userId)
      } else {
        next.add(userId)
      }
      return next
    })
  }

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Address</TableCell>
            <TableCell>Gifts</TableCell>
            <TableCell>Match</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {users.map(user => {
            const isSelf = user.email === currentAdminEmail
            const giftSummary = user.gifts?.length
              ? user.gifts.map(gift => gift.name).join(', ')
              : 'No gifts yet'
            const isRevealed = revealedIds.has(user.id)

            return (
              <TableRow key={user.id}>
                <TableCell>{user.name}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>{user.address}</TableCell>
                <TableCell>{giftSummary}</TableCell>
                <TableCell>
                  {!user.assignedTo
                    ? "Not generated"
                    : (
                      <Button size="small" onClick={() => toggleRevealed(user.id)}>
                        {isRevealed ? user.assignedTo.name : "Reveal"}
                      </Button>
                    )
                  }
                </TableCell>
                <TableCell align="right">
                  <Stack direction="row" spacing={1} justifyContent="flex-end">
                    <Button size="small" onClick={() => onEdit(user)}>Edit</Button>
                    <Button
                      size="small"
                      color="error"
                      disabled={isSelf}
                      title={isSelf ? "You can't delete your own admin account" : undefined}
                      onClick={() => onDelete(user)}
                    >
                      Delete
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default UserTable
