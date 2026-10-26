import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Modal from '../common/Modal';
import { LoginForm, SignupForm } from '../components';
import { useAuth } from './AuthContext';

const AuthModalContext = createContext(null);

const AuthModalProvider = ({ children }) => {
  const { status, user, updateUser, isSignInLink, getEmailForSignIn, completeSignIn } = useAuth()
  const navigate = useNavigate()
  // 'login' | 'signup' (both email a sign-in link), 'confirm' (link opened on another
  // device), 'profile' (signed in, finishing sign-up), or null
  const [openModal, setOpenModal] = useState(null)
  const [linkError, setLinkError] = useState("")
  // Set once a sign-in link completes, so the user lands on their dashboard (or the profile form)
  const [arrivedFromLink, setArrivedFromLink] = useState(false)
  const handledLink = useRef(false)

  // Someone signed in but without a profile can only finish signing up
  const openLogin = () => setOpenModal(status === 'needsProfile' ? 'profile' : 'login')
  const openSignup = () => setOpenModal(status === 'needsProfile' ? 'profile' : 'signup')
  const handleCloseModal = () => { setOpenModal(null); setLinkError("") }

  const handleAuthSuccess = authenticatedUser => {
    updateUser(authenticatedUser)
    handleCloseModal()
    navigate(`/dashboard/${authenticatedUser.id}`)
  }

  // Finish sign-in when the page was opened from an emailed link
  useEffect(() => {
    if (handledLink.current || !isSignInLink()) return
    handledLink.current = true

    const email = getEmailForSignIn()
    if (!email) {
      setOpenModal('confirm')
      return
    }
    completeSignIn(email)
      .then(() => setArrivedFromLink(true))
      .catch(error => {
        console.error('Error completing sign-in:', error)
        setLinkError("This sign-in link has expired or was already used. Request a new one.")
        setOpenModal('login')
      })
  }, [isSignInLink, getEmailForSignIn, completeSignIn])

  // After a link sign-in, wait for the profile to load, then go to the dashboard or finish sign-up
  useEffect(() => {
    if (!arrivedFromLink) return
    if (status === 'ready' && user) {
      setArrivedFromLink(false)
      handleAuthSuccess(user)
    } else if (status === 'needsProfile') {
      setArrivedFromLink(false)
      setOpenModal('profile')
    }
    // handleAuthSuccess is recreated each render; status and user are what matter here
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [arrivedFromLink, status, user])

  return (
    <AuthModalContext.Provider value={{ openLogin, openSignup }}>
      {children}
      <Modal open={openModal === 'login' || openModal === 'signup'} handleCloseModal={handleCloseModal}>
        <LoginForm key={openModal} mode={openModal === 'signup' ? 'signup' : 'login'} initialError={linkError} />
      </Modal>
      <Modal open={openModal === 'confirm'} handleCloseModal={handleCloseModal}>
        <LoginForm mode="confirm" onConfirmed={() => { setOpenModal(null); setArrivedFromLink(true) }} />
      </Modal>
      <Modal open={openModal === 'profile'} handleCloseModal={handleCloseModal}>
        <SignupForm onSignupSuccess={handleAuthSuccess} />
      </Modal>
    </AuthModalContext.Provider>
  )
}

const useAuthModal = () => useContext(AuthModalContext);

export { AuthModalProvider, useAuthModal };
