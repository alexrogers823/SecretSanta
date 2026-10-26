import React, { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch, getErrorMessage } from '../api/client'
import { useAuth } from '../context/AuthContext'

// Browsers fire setTimeout immediately for delays over ~24.8 days, so farther reveals aren't scheduled
const MAX_TIMEOUT_MS = 2 ** 31 - 1

const MatchContext = createContext({ match: null, error: "" })

// Loads the signed-in user's match from /api/matches/me once ({revealed, reveal_at, receiver, gifts})
// and shares it with the header countdown, dashboard and home page. The server decides when it's
// revealed, so they always agree. While the page stays open, it fetches again at reveal time.
export const MatchProvider = ({ children }) => {
  const { user } = useAuth()
  const userId = user?.id
  const [match, setMatch] = useState(null)
  const [error, setError] = useState("")
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => {
    setMatch(null)
    setError("")
    if (!userId) return
    let cancelled = false

    apiFetch("/api/matches/me")
      .then(data => { if (!cancelled) setMatch(data) })
      .catch(fetchError => {
        console.error('Error fetching assignment:', fetchError)
        if (!cancelled) setError(getErrorMessage(fetchError))
      })

    return () => { cancelled = true }
  }, [userId, refreshCount])

  useEffect(() => {
    if (!match || match.revealed || !match.reveal_at) return
    const delay = new Date(match.reveal_at).getTime() - Date.now()
    if (delay > MAX_TIMEOUT_MS) return
    // A second's grace so the server agrees the time has passed
    const timeoutId = setTimeout(() => setRefreshCount(count => count + 1), Math.max(delay, 0) + 1000)
    return () => clearTimeout(timeoutId)
  }, [match])

  return <MatchContext.Provider value={{ match, error }}>{children}</MatchContext.Provider>
}

const useMatch = () => useContext(MatchContext)

export default useMatch
