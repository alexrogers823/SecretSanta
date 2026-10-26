import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ApiError, apiFetch } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { removeProfilePicture, uploadProfilePicture } from '../utils/profilePicture'
import EditProfileForm from './EditProfileForm'
import LoginForm from './LoginForm'
import ProfilePictureInput from './ProfilePictureInput'
import SignupForm from './SignupForm'

jest.mock('../api/client', () => ({
  ...jest.requireActual('../api/client'),
  apiFetch: jest.fn(),
}))
jest.mock('../context/AuthContext', () => ({ useAuth: jest.fn() }))
jest.mock('../utils/profilePicture', () => ({
  ...jest.requireActual('../utils/profilePicture'),
  uploadProfilePicture: jest.fn(),
  removeProfilePicture: jest.fn(),
}))

const USER = { id: 'u1', first_name: 'Ann', last_name: 'Lee', email: 'ann@example.com', address: '1 Elf Rd', profile_picture_url: null }
const picture = new File(['png'], 'me.png', { type: 'image/png' })

beforeEach(() => {
  jest.clearAllMocks()
  global.URL.createObjectURL = jest.fn(() => 'blob:preview')
  global.URL.revokeObjectURL = jest.fn()
})

const choosePicture = file => {
  fireEvent.change(document.querySelector('input[type="file"]'), { target: { files: [file] } })
}

// EditProfileForm (2.2: PATCH /api/me)

test('edits save to /api/me without the email', async () => {
  const onEditSuccess = jest.fn()
  apiFetch.mockResolvedValue({ ...USER, address: '9 Pole Ln' })
  render(<EditProfileForm user={USER} onEditSuccess={onEditSuccess} />)
  fireEvent.change(document.getElementById('address'), { target: { value: '9 Pole Ln' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  await waitFor(() => expect(onEditSuccess).toHaveBeenCalledWith({ ...USER, address: '9 Pole Ln' }))
  expect(apiFetch).toHaveBeenCalledWith('/api/me', {
    method: 'PATCH', body: { first_name: 'Ann', last_name: 'Lee', address: '9 Pole Ln' },
  })
})

test('the email is read-only because it is the sign-in address', () => {
  render(<EditProfileForm user={USER} />)
  expect(document.getElementById('email')).toHaveAttribute('readonly')
})

test('blank fields are caught before saving', async () => {
  render(<EditProfileForm user={USER} />)
  fireEvent.change(document.getElementById('last_name'), { target: { value: '  ' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByText('First name, last name, and address are required.')).toBeInTheDocument()
  expect(apiFetch).not.toHaveBeenCalled()
})

test('server errors are shown', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  apiFetch.mockRejectedValue(new ApiError('address cannot be empty', 400, { error: 'address cannot be empty' }))
  render(<EditProfileForm user={USER} />)
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  expect(await screen.findByText('address cannot be empty')).toBeInTheDocument()
})

test('a new picture is uploaded after the profile saves', async () => {
  const onEditSuccess = jest.fn()
  apiFetch.mockResolvedValue(USER)
  uploadProfilePicture.mockResolvedValue({ ...USER, profile_picture_url: 'https://x/avatars/u1/p.webp' })
  render(<EditProfileForm user={USER} onEditSuccess={onEditSuccess} />)
  choosePicture(picture)
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))

  await waitFor(() => expect(onEditSuccess).toHaveBeenCalledWith({ ...USER, profile_picture_url: 'https://x/avatars/u1/p.webp' }))
  expect(uploadProfilePicture).toHaveBeenCalledWith('u1', picture)
})

test('removing the existing picture calls the remove API', async () => {
  const withPicture = { ...USER, profile_picture_url: 'https://x/avatars/u1/p.webp' }
  apiFetch.mockResolvedValue(withPicture)
  removeProfilePicture.mockResolvedValue(USER)
  const onEditSuccess = jest.fn()
  render(<EditProfileForm user={withPicture} onEditSuccess={onEditSuccess} />)
  fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(onEditSuccess).toHaveBeenCalledWith(USER))
  expect(removeProfilePicture).toHaveBeenCalledWith('u1')
})

// SignupForm with a picture (2.6 + 2.17)

const signupAuth = { email: 'ann@example.com', createProfile: jest.fn(), logout: jest.fn() }

const fillSignup = () => {
  fireEvent.change(document.getElementById('first_name'), { target: { value: 'Ann' } })
  fireEvent.change(document.getElementById('last_name'), { target: { value: 'Lee' } })
  fireEvent.change(document.getElementById('address'), { target: { value: '1 Elf Rd' } })
}

test('sign-up uploads the chosen picture after creating the profile', async () => {
  useAuth.mockReturnValue(signupAuth)
  signupAuth.createProfile.mockResolvedValue({ ...USER, is_admin: false })
  uploadProfilePicture.mockResolvedValue({ ...USER, profile_picture_url: 'https://x/p.webp' })
  const onSignupSuccess = jest.fn()
  render(<SignupForm onSignupSuccess={onSignupSuccess} />)
  fillSignup()
  choosePicture(picture)
  fireEvent.click(screen.getByRole('button', { name: 'Register' }))

  await waitFor(() => expect(onSignupSuccess).toHaveBeenCalledWith({ ...USER, is_admin: false, profile_picture_url: 'https://x/p.webp' }))
  expect(signupAuth.createProfile.mock.invocationCallOrder[0]).toBeLessThan(uploadProfilePicture.mock.invocationCallOrder[0])
})

test('a failed picture upload still finishes sign-up', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  useAuth.mockReturnValue(signupAuth)
  signupAuth.createProfile.mockResolvedValue(USER)
  uploadProfilePicture.mockRejectedValue(new Error('upload failed'))
  const onSignupSuccess = jest.fn()
  render(<SignupForm onSignupSuccess={onSignupSuccess} />)
  fillSignup()
  choosePicture(picture)
  fireEvent.click(screen.getByRole('button', { name: 'Register' }))
  await waitFor(() => expect(onSignupSuccess).toHaveBeenCalledWith(USER))
})

test('sign-up requires every field', async () => {
  useAuth.mockReturnValue(signupAuth)
  render(<SignupForm />)
  fireEvent.click(screen.getByRole('button', { name: 'Register' }))
  expect(await screen.findByText('First name, last name, and address are required.')).toBeInTheDocument()
  expect(signupAuth.createProfile).not.toHaveBeenCalled()
})

// LoginForm details (2.6)

test('after sending a link, "Use a Different Email" returns to the form', async () => {
  useAuth.mockReturnValue({ sendSignInLink: jest.fn().mockResolvedValue(), completeSignIn: jest.fn() })
  render(<LoginForm />)
  fireEvent.change(document.getElementById('email'), { target: { value: 'ann@example.com' } })
  fireEvent.click(screen.getByRole('button', { name: 'Email Me a Link' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Use a Different Email' }))
  expect(screen.getByRole('button', { name: 'Email Me a Link' })).toBeInTheDocument()
})

test('a malformed email gets a clear message', async () => {
  jest.spyOn(console, 'error').mockImplementation(() => {})
  const invalid = Object.assign(new Error('bad'), { code: 'auth/invalid-email' })
  useAuth.mockReturnValue({ sendSignInLink: jest.fn().mockRejectedValue(invalid), completeSignIn: jest.fn() })
  render(<LoginForm />)
  fireEvent.change(document.getElementById('email'), { target: { value: 'not-an-email' } })
  fireEvent.click(screen.getByRole('button', { name: 'Email Me a Link' }))
  expect(await screen.findByText("That email address doesn't look right.")).toBeInTheDocument()
})

// ProfilePictureInput (2.17)

test('the picture picker accepts the server formats, including HEIC', () => {
  render(<ProfilePictureInput file={null} onChange={jest.fn()} />)
  const accept = document.querySelector('input[type="file"]').getAttribute('accept').split(',')
  expect(accept).toEqual(expect.arrayContaining(['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/heic', '.heic']))
})

test('the picture picker rejects unsupported and oversized files', () => {
  const onChange = jest.fn()
  render(<ProfilePictureInput file={null} onChange={onChange} />)
  choosePicture(new File(['x'], 'me.bmp', { type: 'image/bmp' }))
  expect(screen.getByText(/must be a JPEG, PNG, GIF, WebP, or HEIC image/)).toBeInTheDocument()

  const huge = new File(['x'], 'big.png', { type: 'image/png' })
  Object.defineProperty(huge, 'size', { value: 5 * 1024 * 1024 + 1 })
  choosePicture(huge)
  expect(screen.getByText('Profile picture must be 5 MB or smaller')).toBeInTheDocument()
  expect(onChange).not.toHaveBeenCalled()
})
