import { Grid, Stack } from '@mui/material';
import Container from '@mui/material/Container';
import React from "react";
import { Button, PromptCard } from '../../common';
import { DashboardPrompt, PhotoGallery, PhotoUpload } from '../../components';
import { useAuth } from '../../context/AuthContext';
import { useAuthModal } from '../../context/AuthModalContext';

const Main = () => {
  const { user } = useAuth()
  const { openLogin, openSignup } = useAuthModal()

  return (
    <Container maxWidth="md" sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <p>Welcome to Secret Santa!</p>
      <Stack justifyContent="center" sx={{ flex: 1, py: 4 }}>
        <Grid container spacing={4} alignItems="stretch">
          {user
            ? (
              <>
                <Grid item xs={12} md={6}>
                  <PhotoUpload />
                </Grid>
                <Grid item xs={12} md={6}>
                  <DashboardPrompt user={user} />
                </Grid>
              </>
            )
            : (
              <>
                <Grid item xs={12} md={6}>
                  <PromptCard message="Log in to manage gift requests and review your information">
                    <Button variant="contained" onClick={openLogin}>Log In</Button>
                  </PromptCard>
                </Grid>
                <Grid item xs={12} md={6}>
                  <PromptCard message="Sign up and join your LBs in the fun!">
                    <Button variant="contained" onClick={openSignup}>Sign Up</Button>
                  </PromptCard>
                </Grid>
                <Grid item xs={12}>
                  <PhotoGallery />
                </Grid>
              </>
            )
          }
        </Grid>
      </Stack>
    </Container>
  )
}

export default Main
