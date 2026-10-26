import React, { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';

const About = () => {
  const [message, setMessage] = useState("");

  useEffect(() => {
    const fetchData = async () => {
      try {
        setMessage(await apiFetch("/api/about"));
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