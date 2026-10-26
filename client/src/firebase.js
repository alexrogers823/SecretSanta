import { initializeApp } from 'firebase/app'
import { connectAuthEmulator, getAuth } from 'firebase/auth'

// These identify the Firebase project; they aren't secrets (they ship in the browser bundle either way).
// Values come from client/.env.development and client/.env.production.
const config = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID,
}

const missing = Object.entries(config).filter(([, value]) => !value).map(([key]) => key)
if (missing.length) {
  throw new Error(`Firebase config is missing ${missing.join(', ')}. Check client/.env.development or .env.production.`)
}

const app = initializeApp(config)

export const auth = getAuth(app)

// Local development signs in against the Auth emulator, the same one Flask verifies tokens with,
// so it never touches real accounts
if (process.env.REACT_APP_USE_AUTH_EMULATOR === 'true') {
  connectAuthEmulator(auth, 'http://127.0.0.1:9099', { disableWarnings: true })
}
