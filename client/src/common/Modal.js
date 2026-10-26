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
      {/* MUI moves focus into the modal through a ref, which function components like the forms can't hold */}
      <div style={{ outline: 'none' }}>{props.children}</div>
    </MuiModal>
  )
}

export default Modal