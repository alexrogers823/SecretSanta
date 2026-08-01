import { Typography } from '@mui/material';
import { useEffect, useState } from 'react';

const pad2 = n => String(n).padStart(2, '0')

const getTimeRemaining = targetDate => {
  const totalSeconds = Math.floor(Math.max(0, targetDate.getTime() - Date.now()) / 1000)
  return {
    days: Math.floor(totalSeconds / 86400),
    hours: Math.floor((totalSeconds % 86400) / 3600),
    minutes: Math.floor((totalSeconds % 3600) / 60),
    seconds: totalSeconds % 60,
  }
}

const CountdownTimer = ({ label, getTargetDate }) => {
  const [remaining, setRemaining] = useState(() => getTimeRemaining(getTargetDate()))

  useEffect(() => {
    const intervalId = setInterval(() => {
      setRemaining(getTimeRemaining(getTargetDate()))
    }, 1000)
    return () => clearInterval(intervalId)
  }, [getTargetDate])

  const { days, hours, minutes, seconds } = remaining

  return (
    <Typography component="span" sx={{ whiteSpace: 'nowrap' }}>
      {`${label}: ${days}d ${pad2(hours)}h ${pad2(minutes)}m ${pad2(seconds)}s`}
    </Typography>
  )
}

export default CountdownTimer
