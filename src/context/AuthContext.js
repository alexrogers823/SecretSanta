import React, { createContext, useContext, useState } from 'react';

const STORAGE_KEY = 'secretSantaUser';
const ADMIN_EMAIL = 'alex.rogers823@gmail.com';

const AuthContext = createContext(null);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    const storedUser = stored ? JSON.parse(stored) : null;
    // Users saved before the first/last name split need to log in again to load their new profile shape
    return storedUser?.first_name ? storedUser : null;
  });

  const login = (loggedInUser) => {
    setUser(loggedInUser);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(loggedInUser));
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => useContext(AuthContext);

const isAdmin = (user) => user?.email === ADMIN_EMAIL;

export { AuthProvider, useAuth, isAdmin };
