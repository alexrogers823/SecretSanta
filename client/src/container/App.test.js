import { act, render, screen } from '@testing-library/react';
import { onAuthStateChanged } from 'firebase/auth';
import { apiFetch } from '../api/client';
import Ornament from '../modules/UserDashboard/Ornament';
import App from './App';

jest.mock('firebase/auth', () => ({
  isSignInWithEmailLink: jest.fn(() => false),
  onAuthStateChanged: jest.fn(),
  sendSignInLinkToEmail: jest.fn(),
  signInWithEmailLink: jest.fn(),
  signOut: jest.fn(),
}));
jest.mock('../api/client', () => ({
  ...jest.requireActual('../api/client'),
  apiFetch: jest.fn(),
}));

const renderApp = async firebaseUser => {
  onAuthStateChanged.mockImplementation((auth, callback) => {
    callback(firebaseUser);
    return () => {};
  });
  render(<App />);
  await act(async () => {});
};

beforeEach(() => jest.clearAllMocks());

test('signed-out home page', async () => {
  apiFetch.mockResolvedValue({ season: 2026, seasons: [2026], photos: [] });
  await renderApp(null);
  expect(screen.getByText('Secret Santa X')).toBeInTheDocument();
  expect(screen.getByText('Welcome to Secret Santa!')).toBeInTheDocument();
  expect(screen.getAllByRole('button', { name: 'Log In' })).toHaveLength(2);  // header and home card
  expect(screen.getAllByRole('button', { name: 'Sign Up' })).toHaveLength(2);
  expect(screen.getByRole('button', { name: 'Ask Question' })).toBeInTheDocument();
  // Visitors see the public gallery; nothing that needs sign-in is requested
  expect(screen.getByText('Christmas Photos')).toBeInTheDocument();
  expect(apiFetch.mock.calls.map(([path]) => path)).toEqual(['/api/photos']);
});

test('signed-in home page loads the profile and match', async () => {
  apiFetch.mockImplementation(async path => (
    path === '/api/me'
      ? { id: 'u1', first_name: 'Ann', last_name: 'Lee', email: 'ann@example.com', address: '1 Elf Rd', is_admin: false }
      : { revealed: false, reveal_at: '2099-11-25T17:00:00+00:00' }
  ));
  await renderApp({ email: 'ann@example.com' });

  expect(screen.getByText('Ann')).toBeInTheDocument();  // "Logged In as Ann" in the header
  expect(screen.getByRole('button', { name: 'Go to Dashboard' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Log Out' })).toBeInTheDocument();
  expect(apiFetch).toHaveBeenCalledWith('/api/me');
  expect(apiFetch).toHaveBeenCalledWith('/api/matches/me');
});

test('theme images come from the assets bucket', () => {
  process.env.REACT_APP_ASSETS_URL = 'https://storage.googleapis.com/secret-santa-assets';
  render(<Ornament />);
  expect(screen.getByRole('img')).toHaveAttribute(
    'src', 'https://storage.googleapis.com/secret-santa-assets/img/ornament.webp',
  );
});
