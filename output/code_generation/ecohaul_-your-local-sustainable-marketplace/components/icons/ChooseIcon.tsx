import React from 'react';

const ChooseIcon: React.FC = () => (
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
        <path d="M10.5 21h-4.5a2 2 0 0 1 -2 -2v-12a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v3.5" />
        <path d="M4 11h16" />
        <path d="M7 16h3" />
        <path d="M7 7v-2" />
        <path d="M17 7v-2" />
        <path d="M19 16l-2 3h4l-2 3" />
    </svg>
);

export default ChooseIcon;
