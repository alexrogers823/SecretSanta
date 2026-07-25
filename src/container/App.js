import React from 'react';
import {
  Route,
  BrowserRouter as Router,
  Routes
} from "react-router-dom";
import About from '../modules/About';
import Main from '../modules/Main';

const App = () => {
  return (
    <div>
      <Router>
        <div>
          <Routes>
            <Route path="/about" element={<About />} />
            <Route path="/" element={<Main />} />
          </Routes>
        </div>
      </Router>
    </div>
  )
}

export default App