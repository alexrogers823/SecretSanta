import { initializeApp } from 'firebase/app'
import { connectAuthEmulator, getAuth } from 'firebase/auth'

// setupTests.js mocks ./firebase for every other test; here we load the real module
jest.unmock('./firebase')
jest.mock('firebase/app', () => ({ initializeApp: jest.fn() }))
jest.mock('firebase/auth', () => ({ getAuth: jest.fn(), connectAuthEmulator: jest.fn() }))

const CONFIG_ENV = {
  REACT_APP_FIREBASE_API_KEY: 'key',
  REACT_APP_FIREBASE_AUTH_DOMAIN: 'secret-santa-511801.firebaseapp.com',
  REACT_APP_FIREBASE_PROJECT_ID: 'secret-santa-511801',
  REACT_APP_FIREBASE_APP_ID: '1:2:web:3',
}
const originalEnv = process.env

const loadFirebase = env => {
  process.env = { ...originalEnv, ...env }
  let module
  jest.isolateModules(() => { module = require('./firebase') })
  return module
}

// CRA's Jest config resets mock implementations before each test, so set them here
beforeEach(() => {
  initializeApp.mockReturnValue('app')
  getAuth.mockReturnValue({ name: 'auth' })
})
afterEach(() => { process.env = originalEnv })

test('initializes the app from the REACT_APP_FIREBASE_* settings and exports auth', () => {
  const { auth } = loadFirebase(CONFIG_ENV)
  expect(initializeApp).toHaveBeenCalledWith({
    apiKey: 'key',
    authDomain: 'secret-santa-511801.firebaseapp.com',
    projectId: 'secret-santa-511801',
    appId: '1:2:web:3',
  })
  expect(getAuth).toHaveBeenCalledWith('app')
  expect(auth).toEqual({ name: 'auth' })
})

test('names any missing setting instead of failing obscurely', () => {
  expect(() => loadFirebase({ ...CONFIG_ENV, REACT_APP_FIREBASE_API_KEY: '', REACT_APP_FIREBASE_APP_ID: undefined }))
    .toThrow('Firebase config is missing apiKey, appId')
  expect(initializeApp).not.toHaveBeenCalled()
})

test('development connects to the Auth emulator that Flask also uses', () => {
  loadFirebase({ ...CONFIG_ENV, REACT_APP_USE_AUTH_EMULATOR: 'true' })
  expect(connectAuthEmulator).toHaveBeenCalledWith({ name: 'auth' }, 'http://127.0.0.1:9099', { disableWarnings: true })
})

test('production uses real Firebase Auth', () => {
  loadFirebase({ ...CONFIG_ENV, REACT_APP_USE_AUTH_EMULATOR: undefined })
  expect(connectAuthEmulator).not.toHaveBeenCalled()
})
