import CardGiftcardOutlinedIcon from '@mui/icons-material/CardGiftcardOutlined';
import { Stack, TextField } from '@mui/material';
import React, { Fragment, useEffect, useState } from 'react';
import { Button, Form } from '../common';

const XmasForm = props => {
  const [giftCounter, setGiftCounter] = useState(1)
  const [showButton, setShowButton] = useState(true)
  const giftOptions = [
    { id: "firstOption", label: "First Option", required: true },
    { id: "secondOption", label: "Second Option", required: false },
    { id: "thirdOption", label: "Third Option", required: false },
    { id: "fourthOption", label: "Fourth Option", required: false }
  ]

  useEffect(() => {
    if (giftCounter > 3) {
      setShowButton(false)
    }
  }, [giftCounter])

  const handleGiftCounter = () => {
    console.log(giftCounter)
    if (giftCounter < 4) {
      setGiftCounter(counter => counter + 1)
    }
  }

  return (
    <Form
      title="Bro. KT's Form"
      actions={showButton && <Button onClick={handleGiftCounter} endIcon={<CardGiftcardOutlinedIcon />}>Add</Button>}
    >
      <Stack direction="column" spacing={2}>
        <TextField id="address" label="Address" variant="standard" multiline required fullWidth/>
        {giftOptions.slice(0, giftCounter).map((option, index) => (
          <Fragment key={index+1}>
            <TextField id={option.id} label={option.label} variant="standard" required={option.required} fullWidth />
            <TextField id={`${option.id}Url`} label="URL (optional)" variant="standard" fullWidth />
            <TextField id={`${option.id}Notes`} label="Notes" variant="standard" fullWidth />
          </Fragment>
        ))}
      </Stack>
    </Form>
  )
}

export default XmasForm

