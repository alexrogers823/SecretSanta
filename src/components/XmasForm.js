import CardGiftcardOutlinedIcon from '@mui/icons-material/CardGiftcardOutlined';
import { Stack, TextField } from '@mui/material';
import React, { Fragment, useEffect, useState } from 'react';
import { Button, Form } from '../common';

export const GIFT_OPTIONS = [
  { id: "firstOption", label: "First Option", required: true },
  { id: "secondOption", label: "Second Option", required: false },
  { id: "thirdOption", label: "Third Option", required: false },
  { id: "fourthOption", label: "Fourth Option", required: false }
]

const XmasForm = ({ initialValues, onSubmit }) => {
  const filledCount = GIFT_OPTIONS.filter(option => initialValues?.[option.id]).length
  const [giftCounter, setGiftCounter] = useState(Math.max(filledCount, 1))
  const [showButton, setShowButton] = useState(giftCounter <= 3)

  useEffect(() => {
    if (giftCounter > 3) {
      setShowButton(false)
    }
  }, [giftCounter])

  const handleGiftCounter = () => {
    if (giftCounter < 4) {
      setGiftCounter(counter => counter + 1)
    }
  }

  return (
    <Form
      title="Bro. KT's Form"
      onSubmit={onSubmit}
      actions={showButton && <Button onClick={handleGiftCounter} endIcon={<CardGiftcardOutlinedIcon />}>Add</Button>}
    >
      <Stack direction="column" spacing={2}>
        {GIFT_OPTIONS.slice(0, giftCounter).map((option, index) => (
          <Fragment key={index+1}>
            <TextField id={option.id} label={option.label} variant="standard" defaultValue={initialValues?.[option.id]} required={option.required} fullWidth />
            <TextField id={`${option.id}Url`} label="URL (optional)" variant="standard" defaultValue={initialValues?.[`${option.id}Url`]} fullWidth />
            <TextField id={`${option.id}Notes`} label="Notes" variant="standard" defaultValue={initialValues?.[`${option.id}Notes`]} fullWidth />
          </Fragment>
        ))}
      </Stack>
    </Form>
  )
}

export default XmasForm

