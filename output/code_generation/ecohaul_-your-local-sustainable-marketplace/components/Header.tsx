import React, { useState } from 'react';

const LeafIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-6 w-6 inline-block text-brand-green"
    fill="none"
    viewBox="0 0 24 24"
    stroke="currentColor"
    strokeWidth={2}
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
    />
  </svg>
);

const CartIcon: React.FC<{ count: number }> = ({ count }) => (
  <div className="relative">
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-brand-gray-dark group-hover:text-brand-green transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
    </svg>
    {count > 0 && (
      <span className="absolute -top-2 -right-3 bg-red-500 text-white text-xs w-5 h-5 flex items-center justify-center rounded-full font-bold">
        {count}
      </span>
    )}
  </div>
);

const Header: React.FC<{ cartCount: number; onCartClick: () => void; }> = ({ cartCount, onCartClick }) => {
  const [isOpen, setIsOpen] = useState(false);

  const navLinks = [
    { name: 'Our Mission', href: '#mission' },
    { name: 'Products', href: '#products' },
    { name: 'How It Works', href: '#how-it-works' },
    { name: 'Vendors', href: '#vendors' },
  ];

  return (
    <header className="bg-white/80 backdrop-blur-md sticky top-0 z-40 shadow-sm">
      <div className="container mx-auto px-6 py-3">
        <div className="flex items-center justify-between">
          <a href="#" className="flex items-center gap-2">
            <LeafIcon />
            <span className="text-2xl font-bold text-brand-green-dark font-serif">
              EcoHaul
            </span>
          </a>
          <div className="hidden md:flex items-center space-x-8">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="text-brand-gray-dark hover:text-brand-green transition-colors duration-300"
              >
                {link.name}
              </a>
            ))}
          </div>
          <div className="flex items-center gap-4">
            <a
              href="#products"
              className="hidden md:inline-block bg-brand-green text-white font-bold py-2 px-6 rounded-full hover:bg-brand-green-dark transition-all duration-300 transform hover:scale-105"
            >
              Shop Now
            </a>
             <button onClick={onCartClick} className="p-2 rounded-full group" aria-label={`Open cart with ${cartCount} items`}>
                <CartIcon count={cartCount} />
            </button>
            <div className="md:hidden">
              <button
                onClick={() => setIsOpen(!isOpen)}
                className="text-brand-gray-dark focus:outline-none"
                aria-label="Open menu"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  {isOpen ? (
                    <path d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path d="M4 6h16M4 12h16m-7 6h7" />
                  )}
                </svg>
              </button>
            </div>
          </div>
        </div>
        {isOpen && (
          <div className="md:hidden mt-4">
            <div className="flex flex-col items-center space-y-4">
              {navLinks.map((link) => (
                <a
                  key={link.name}
                  href={link.href}
                  onClick={() => setIsOpen(false)}
                  className="text-brand-gray-dark hover:text-brand-green transition-colors duration-300"
                >
                  {link.name}
                </a>
              ))}
              <a
                href="#products"
                onClick={() => setIsOpen(false)}
                className="bg-brand-green text-white font-bold py-2 px-6 rounded-full hover:bg-brand-green-dark transition-all duration-300"
              >
                Shop Now
              </a>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;