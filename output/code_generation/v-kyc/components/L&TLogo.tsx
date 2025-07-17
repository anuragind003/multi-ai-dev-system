import React from 'react';

interface LTLogoProps {
  className?: string;
  width?: number;
  height?: number;
}

const LTLogo: React.FC<LTLogoProps> = ({ className = '', width = 200, height = 80 }) => (
  <div className={`flex items-center justify-center ${className}`}>
    <img 
      src="/L&T.jpg" 
      alt="L&T Finance Logo" 
      width={width} 
      height={height}
      className="object-contain"
      style={{ maxWidth: '100%', height: 'auto' }}
    />
  </div>
);

export default LTLogo;
