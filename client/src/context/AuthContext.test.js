import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import {
  isSignInWithEmailLink,
  onAuthStateChanged,
  sendSignInLinkToEmail,
  signInWithEmailLink,
  signOut,
} from 'firebase/auth'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { ApiError, apiFetch } from '../api/client'
import { AuthProvider, isAdmin, useAuth } from './AuthContext'
import { AuthModalProvider, useAuthModal } from './AuthModalContext'

jest.mock('firebase/auth', () => ({
  isSignInWithEmailLink: jest.fn(),
  onAuthStateChanged: jest.fn(),
  sendSignInLinkToEmail: jest.fn(),
  signInWithEmailLink: jest.fn(),
  signOut: jest.fn(),
}))
jest.mock('../api/client', () => ({
  ...jest.requireActual('../api/client'),
  apiFetch: jest.fn(),
}))
// The profile picture input pulls in browser-only bits that aren't under test here
jest.mock('../components/ProfilePictureInput', () => () => null)

const PROFILE = { id: 'u1', first_name: 'Ann', last_name: 'Lee', email: 'ann@example.com', address: '1 Elf Rd', is_admin: false }
const notFound = () => new ApiError('profile not found', 404, { error: 'profile not found' })

// Lets a test decide when Firebase reports the session, like the real SDK does asynchronously
let reportAuthState
beforeEach(() => {
  jest.clearAllMocks()
  localStorage.clear()
  isSignInWithEmailLink.mockReturnValue(false)
  onAuthStateChanged.mockImplementation((auth, callback) => {
    reportAuthState = callback
    return () => {}
  })
})

const signIn = async (firebaseUser = { email: 'ann@example.com' }) => {
  await act(async () => { await reportAuthState(firebaseUser) })
}

const Status = () => {
  const { status, user, email } = useAuth()
  return <div data-testid="status">{`${status}|${user?.first_name || ''}|${email || ''}`}</div>
}

const AuthButtons = () => {
  const { openLogin, openSignup } = useAuthModal()
  return (
    <>
      <button onClick={openLogin}>open login</button>
      <button onClick={openSignup}>open signup</button>
    </>
  )
}

const Location = () => <div data-testid="location">{useLocation().pathname}</div>

const renderApp = () => render(
  <MemoryRouter>
    <AuthProvider>
      <AuthModalProvider>
        <Status />
        <AuthButtons />
        <Routes><Route path="*" element={<Location />} /></Routes>
      </AuthModalProvider>
    </AuthProvider>
  </MemoryRouter>
)

const fillAndSubmit = (fields, buttonName) => {
  Object.entries(fields).forEach(([id, value]) => {
    fireEvent.change(document.getElementById(id), { target: { value } })
  })
  fireEvent.click(screen.getByRole('button', { name: buttonName }))
}

// AuthContext (2.5)

test('is loading until Firebase reports the session', () => {
  renderApp()
  expect(screen.getByTestId('status')).toHaveTextContent('loading')
})

test('signed out', async () => {
  renderApp()
  await signIn(null)
  expect(screen.getByTestId('status')).toHaveTextContent('signedOut||')
})

test('signed in with a profile loads it from /api/me', async () => {
  apiFetch.mockResolvedValue(PROFILE)
  renderApp()
  await signIn()
  expect(apiFetch).toHaveBeenCalledWith('/api/me')
  expect(screen.getByTestId('status')).toHaveTextContent('ready|Ann|ann@example.com')
})

test('signed in without a profile needs to finish signing up', async () => {
  apiFetch.mockRejectedValue(notFound())
  renderApp()
  await signIn()
  expect(screen.getByTestId('status')).toHaveTextContent('needsProfile||ann@example.com')
})

test('other profile errors are reported, not treated as signup', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  apiFetch.mockRejectedValue(new TypeError('Failed to fetch'))
  renderApp()
  await signIn()
  expect(screen.getByTestId('status')).toHaveTextContent('error')
})

test('clears the user stored by the old localStorage login', () => {
  localStorage.setItem('secretSantaUser', JSON.stringify(PROFILE))
  renderApp()
  expect(localStorage.getItem('secretSantaUser')).toBeNull()
})

test('isAdmin trusts only the server flag', () => {
  expect(isAdmin({ ...PROFILE, is_admin: true })).toBe(true)
  expect(isAdmin({ ...PROFILE, email: 'alex.rogers823@gmail.com' })).toBe(false)
  expect(isAdmin(null)).toBe(false)
})

// Sign-in links and modals (2.6)

test('Log In emails a sign-in link back to this site and remembers the address', async () => {
  sendSignInLinkToEmail.mockResolvedValue()
  renderApp()
  await signIn(null)
  fireEvent.click(screen.getByText('open login'))
  fillAndSubmit({ email: ' ann@example.com ' }, 'Email Me a Link')

  expect(await screen.findByText(/We sent a sign-in link to ann@example.com/)).toBeInTheDocument()
  expect(sendSignInLinkToEmail).toHaveBeenCalledWith(
    expect.anything(), 'ann@example.com', { url: 'http://localhost/', handleCodeInApp: true },
  )
  expect(localStorage.getItem('secretSantaEmailForSignIn')).toBe('ann@example.com')
})

test('Sign Up uses the same link form with sign-up wording', async () => {
  renderApp()
  await signIn(null)
  fireEvent.click(screen.getByText('open signup'))
  expect(screen.getByText('Sign Up for Secret Santa')).toBeInTheDocument()
})

test('the link form requires an email', async () => {
  renderApp()
  await signIn(null)
  fireEvent.click(screen.getByText('open login'))
  fillAndSubmit({}, 'Email Me a Link')
  expect(await screen.findByText('Email is required.')).toBeInTheDocument()
  expect(sendSignInLinkToEmail).not.toHaveBeenCalled()
})

test('opening the link on the same device signs in and goes to the dashboard', async () => {
  isSignInWithEmailLink.mockReturnValue(true)
  localStorage.setItem('secretSantaEmailForSignIn', 'ann@example.com')
  signInWithEmailLink.mockResolvedValue()
  apiFetch.mockResolvedValue(PROFILE)

  renderApp()
  await waitFor(() => expect(signInWithEmailLink).toHaveBeenCalledWith(expect.anything(), 'ann@example.com', 'http://localhost/'))
  await signIn()

  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/dashboard/u1'))
  expect(localStorage.getItem('secretSantaEmailForSignIn')).toBeNull()
})

test('a first sign-in without a profile opens the finish-signing-up form', async () => {
  isSignInWithEmailLink.mockReturnValue(true)
  localStorage.setItem('secretSantaEmailForSignIn', 'ann@example.com')
  signInWithEmailLink.mockResolvedValue()
  apiFetch.mockRejectedValue(notFound())

  renderApp()
  await waitFor(() => expect(signInWithEmailLink).toHaveBeenCalled())
  await signIn()

  expect(await screen.findByText('Finish Signing Up')).toBeInTheDocument()
  expect(document.getElementById('email')).toHaveValue('ann@example.com')
})

test('finishing sign-up creates the profile and goes to the dashboard', async () => {
  apiFetch.mockRejectedValueOnce(notFound())
  renderApp()
  await signIn()
  fireEvent.click(screen.getByText('open signup'))

  apiFetch.mockResolvedValueOnce(PROFILE)
  fillAndSubmit({ first_name: 'Ann', last_name: 'Lee', address: '1 Elf Rd' }, 'Register')

  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/dashboard/u1'))
  expect(apiFetch).toHaveBeenLastCalledWith('/api/me', {
    method: 'POST', body: { first_name: 'Ann', last_name: 'Lee', address: '1 Elf Rd' },
  })
  expect(screen.getByTestId('status')).toHaveTextContent('ready|Ann')
})

test('finishing sign-up shows the server error, e.g. not invited', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  apiFetch.mockRejectedValueOnce(notFound())
  renderApp()
  await signIn()
  fireEvent.click(screen.getByText('open login'))

  const notInvited = "this email hasn't been invited to Secret Santa"
  apiFetch.mockRejectedValueOnce(new ApiError(notInvited, 403, { error: notInvited }))
  fillAndSubmit({ first_name: 'Ann', last_name: 'Lee', address: '1 Elf Rd' }, 'Register')
  expect(await screen.findByText(notInvited)).toBeInTheDocument()
})

test('"Use a Different Email" on the sign-up form signs out', async () => {
  apiFetch.mockRejectedValueOnce(notFound())
  renderApp()
  await signIn()
  fireEvent.click(screen.getByText('open signup'))
  fireEvent.click(screen.getByRole('button', { name: 'Use a Different Email' }))
  expect(signOut).toHaveBeenCalled()
})

test('a link opened on another device asks for the email first', async () => {
  isSignInWithEmailLink.mockReturnValue(true)
  signInWithEmailLink.mockResolvedValue()
  apiFetch.mockResolvedValue(PROFILE)

  renderApp()
  expect(await screen.findByText('Confirm Your Email')).toBeInTheDocument()
  expect(signInWithEmailLink).not.toHaveBeenCalled()

  fillAndSubmit({ email: 'ann@example.com' }, 'Log In')
  await waitFor(() => expect(signInWithEmailLink).toHaveBeenCalledWith(expect.anything(), 'ann@example.com', 'http://localhost/'))
  await signIn()
  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/dashboard/u1'))
})

test('an expired link explains what to do', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  isSignInWithEmailLink.mockReturnValue(true)
  localStorage.setItem('secretSantaEmailForSignIn', 'ann@example.com')
  signInWithEmailLink.mockRejectedValue(Object.assign(new Error('expired'), { code: 'auth/invalid-action-code' }))

  renderApp()
  expect(await screen.findByText(/expired or was already used/)).toBeInTheDocument()
})
