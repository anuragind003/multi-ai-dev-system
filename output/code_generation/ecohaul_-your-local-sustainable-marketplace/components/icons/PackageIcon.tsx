import React from 'react';

const PackageIcon: React.FC = () => (
    <svg 
        xmlns="http://www.w3.org/2000/svg" 
        className="h-10 w-10 text-brand-green group-hover:text-white transition-colors duration-300"
        viewBox="0 0 24 24" 
        strokeWidth="1.5" 
        stroke="currentColor" 
        fill="none" 
        strokeLinecap="round" 
        strokeLinejoin="round">
        <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
        <path d="M12 3l8 4.5v9l-8 4.5l-8 -4.5v-9l8 -4.5" />
        <path d="M12 12l8 -4.5" />
        <path d="M12 12v9" />
        <path d="M12 12l-8 -4.5" />
        <path d="M16 5.25l-8 4.5" />
        <path d="M8.224 13.433c.225 .407 .523 .766 .876 1.057" />
        <path d="M11 19c0 -2.21 -2.239 -4 -5 -4" />
    </svg>
);

export default PackageIcon;
