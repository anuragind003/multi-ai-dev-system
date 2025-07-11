import React from 'react';
import Input from '../components/Input';
import Button from '../components/Button';

const Contact: React.FC = () => {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">Contact Us</h1>
      <form>
        <Input type="text" id="name" name="name" label="Name" />
        <Input type="email" id="email" name="email" label="Email" />
        <Input type="textarea" id="message" name="message" label="Message" />
        <Button type="submit" variant="primary">Submit</Button>
      </form>
    </div>
  );
};

export default Contact;