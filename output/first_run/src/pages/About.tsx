import React from 'react';
import Card from '../components/Card';

const About: React.FC = () => {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">About Us</h1>
      <Card>
        <p>Learn more about our company and mission.</p>
      </Card>
    </div>
  );
};

export default About;