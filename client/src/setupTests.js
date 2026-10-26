// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Tests never talk to the real Firebase project (and .env.development isn't loaded under Jest)
jest.mock('./firebase', () => ({ auth: { currentUser: null } }));
