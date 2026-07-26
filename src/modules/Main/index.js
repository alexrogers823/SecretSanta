import Container from '@mui/material/Container';
import React, { useEffect, useState } from "react";
import { Box } from '../../common';

const Main = () => {
  const [message, setMessage] = useState({})

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("http://localhost:8000/api")
        if (!response.ok) {
          throw new Error('Network response failed');
        }
        const jsonData = await response.json();
        setMessage(jsonData);
      } catch (error) {
        console.error('Error fetching data:', error)
      }
    }

    fetchData();
  }, []);

  return (
    <Container maxWidth="sm">
      <p>Welcome to Secret Santa!</p>
      <Box title={"Signup or login to start adding your desired gifts and other information"} />
    </Container>
  )
}

export default Main
