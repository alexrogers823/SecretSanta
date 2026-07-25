import { Modal as MuiModal } from '@mui/material';
import React from 'react';

const Modal = (props) => {
  const {open, handleCloseModal} = props

  return (
    <MuiModal
      open={open}
      onClose={handleCloseModal}
      aria-labelledby="modal-modal-title"
      aria-describedby="modal-modal-description"
    >
      {props.children}
    </MuiModal>
  )
}

export default Modal