import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, PromptCard } from '../common';
import useMatch from '../hooks/useMatch';

const DashboardPrompt = ({ user }) => {
  const navigate = useNavigate()
  // Same server flag as the dashboard, so the two can't disagree
  const { match } = useMatch()

  return (
    <PromptCard
      message={match?.revealed
        ? `It's here ${user.first_name}! Check who your person is`
        : `${user.first_name}, add your information and gift requests before the reveal date`}
    >
      <Button variant="contained" onClick={() => navigate(`/dashboard/${user.id}`)}>Go to Dashboard</Button>
    </PromptCard>
  )
}

export default DashboardPrompt
