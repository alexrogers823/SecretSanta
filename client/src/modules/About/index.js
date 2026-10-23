import React, { useEffect, useState } from 'react';

const About = () => {
  const [message, setMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/about")
        if (!response.ok) {
          throw new Error('Network response failed');
        }
        const textData = await response.text();
        setMessage(textData);
      } catch (error) {
        console.error('Error fetching data:', error)
      }
    }

    fetchData();
  }, []);

  return (
    <p>{message}</p>
  )
}

export default About;