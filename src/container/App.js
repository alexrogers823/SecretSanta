import React from 'react';
import {
  Route,
  BrowserRouter as Router,
  Routes
} from "react-router-dom";
import { Header } from '../common';
import { AuthProvider } from '../context/AuthContext';
import About from '../modules/About';
import AdminPage from '../modules/Admin';
import Main from '../modules/Main';
import UserDashboard from '../modules/UserDashboard';

const App = () => {
  return (
    <div>
      <Router>
        <AuthProvider>
          <div>
            <Header />
            <Routes>
              <Route path="/about" element={<About />} />
              <Route path="/dashboard/:userId" element={<UserDashboard />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/" element={<Main />} />
            </Routes>
          </div>
        </AuthProvider>
      </Router>
    </div>
  )
}

export default App