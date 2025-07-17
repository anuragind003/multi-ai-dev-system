import React from 'react';

const DeliveryIcon: React.FC = () => (
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
        <circle cx="7" cy="17" r="2" />
        <circle cx="17" cy="17" r="2" />
        <path d="M5 17h-2v-6l2 -5h9l4 5h-3m-4 0h-5" />
        <path d="M14.5 13.5h-1.5v-2.5" />
        <path d="M12 19l-1.5 -3.37a.83 .83 0 0 1 .37 -1.01l.2 -.12" />
    </svg>
);

export default DeliveryIcon;
