import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, PromptCard } from '../common';
import { isMatchRevealed } from '../utils/dateHelpers';

const DashboardPrompt = ({ user }) => {
  const navigate = useNavigate()
  const [revealed, setRevealed] = useState(isMatchRevealed)

  useEffect(() => {
    const intervalId = setInterval(() => setRevealed(isMatchRevealed()), 1000)
    return () => clearInterval(intervalId)
  }, [])

  return (
    <PromptCard
      message={revealed
        ? `It's here ${user.first_name}! Check who your person is`
        : `${user.first_name}, add your information and gift requests before the reveal date`}
    >
      <Button variant="contained" onClick={() => navigate(`/dashboard/${user.id}`)}>Go to Dashboard</Button>
    </PromptCard>
  )
}

export default DashboardPrompt
