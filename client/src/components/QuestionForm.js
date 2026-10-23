import { TextField } from '@mui/material';
import React from 'react';
import { Form } from '../common';


const QuestionForm = props => {
 return (
  <Form
    title="Questions of clarifications for Bro. T4ought"
    submitButtonText="Submit Question"
  >
    <TextField id="questions" multiline required />
  </Form>
 ) 
}

export default QuestionForm