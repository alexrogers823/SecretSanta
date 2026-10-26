import {
  isSignInWithEmailLink,
  onAuthStateChanged,
  sendSignInLinkToEmail,
  signInWithEmailLink,
  signOut,
} from 'firebase/auth';
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { ApiError, apiFetch, setAuthTokenProvider } from '../api/client';
import { auth } from '../firebase';

// Remembers which address the sign-in link was sent to, so clicking it on the same device just works
const EMAIL_FOR_SIGN_IN_KEY = 'secretSantaEmailForSignIn';
// Where the pre-Firebase app kept the logged-in user; cleared so stale data doesn't linger
const LEGACY_USER_KEY = 'secretSantaUser';

// Every API call sends the signed-in user's ID token (Firebase refreshes it as needed)
setAuthTokenProvider(() => auth.currentUser?.getIdToken() ?? null);

const AuthContext = createContext(null);

const AuthProvider = ({ children }) => {
  // 'loading' until Firebase reports the session, then 'signedOut', 'needsProfile'
  // (signed in but hasn't finished signing up), 'ready', or 'error' (profile couldn't load)
  const [status, setStatus] = useState('loading');
  const [user, setUser] = useState(null);
  const [email, setEmail] = useState(null);

  useEffect(() => {
    localStorage.removeItem(LEGACY_USER_KEY);

    return onAuthStateChanged(auth, async firebaseUser => {
      if (!firebaseUser) {
        setUser(null);
        setEmail(null);
        setStatus('signedOut');
        return;
      }

      setEmail(firebaseUser.email);
      try {
        setUser(await apiFetch('/api/me'));
        setStatus('ready');
      } catch (error) {
        setUser(null);
        if (error instanceof ApiError && error.status === 404) {
          setStatus('needsProfile');
        } else {
          console.error('Error loading profile:', error);
          setStatus('error');
        }
      }
    });
  }, []);

  const sendSignInLink = useCallback(async address => {
    await sendSignInLinkToEmail(auth, address, {
      url: `${window.location.origin}/`,
      handleCodeInApp: true,
    });
    localStorage.setItem(EMAIL_FOR_SIGN_IN_KEY, address);
  }, []);

  const isSignInLink = useCallback(() => isSignInWithEmailLink(auth, window.location.href), []);

  // Returns the email the link was sent to on this device, or null if it was opened elsewhere
  const getEmailForSignIn = useCallback(() => localStorage.getItem(EMAIL_FOR_SIGN_IN_KEY), []);

  const completeSignIn = useCallback(async address => {
    await signInWithEmailLink(auth, address, window.location.href);
    localStorage.removeItem(EMAIL_FOR_SIGN_IN_KEY);
    // Drop the one-time code from the address bar so a refresh doesn't try to reuse it
    window.history.replaceState(null, '', window.location.pathname);
  }, []);

  const createProfile = useCallback(async fields => {
    const created = await apiFetch('/api/me', { method: 'POST', body: fields });
    setUser(created);
    setStatus('ready');
    return created;
  }, []);

  // Merges an updated profile from the API (e.g. after editing it)
  const updateUser = useCallback(updatedUser => {
    setUser(current => ({ ...current, ...updatedUser }));
  }, []);

  const logout = useCallback(() => signOut(auth), []);

  return (
    <AuthContext.Provider value={{
      user,
      email,
      status,
      loading: status === 'loading',
      sendSignInLink,
      isSignInLink,
      getEmailForSignIn,
      completeSignIn,
      createProfile,
      updateUser,
      logout,
    }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => useContext(AuthContext);

// The server decides who's an admin (ADMIN_EMAILS) and enforces it on every admin route;
// this only decides whether to show admin links
const isAdmin = (user) => user?.is_admin === true;

export { AuthProvider, isAdmin, useAuth };
