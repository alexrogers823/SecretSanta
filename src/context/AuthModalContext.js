import React, { createContext, useContext, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Modal from '../common/Modal';
import { LoginForm, SignupForm } from '../components';
import { useAuth } from './AuthContext';

const AuthModalContext = createContext(null);

const AuthModalProvider = ({ children }) => {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [openModal, setOpenModal] = useState(null)

  const openLogin = () => setOpenModal('login')
  const openSignup = () => setOpenModal('signup')
  const handleCloseModal = () => setOpenModal(null)

  const handleAuthSuccess = authenticatedUser => {
    login(authenticatedUser)
    handleCloseModal()
    navigate(`/dashboard/${authenticatedUser.id}`)
  }

  return (
    <AuthModalContext.Provider value={{ openLogin, openSignup }}>
      {children}
      <Modal open={openModal === 'login'} handleCloseModal={handleCloseModal}>
        <LoginForm onLoginSuccess={handleAuthSuccess} />
      </Modal>
      <Modal open={openModal === 'signup'} handleCloseModal={handleCloseModal}>
        <SignupForm onSignupSuccess={handleAuthSuccess} />
      </Modal>
    </AuthModalContext.Provider>
  )
}

const useAuthModal = () => useContext(AuthModalContext);

export { AuthModalProvider, useAuthModal };
