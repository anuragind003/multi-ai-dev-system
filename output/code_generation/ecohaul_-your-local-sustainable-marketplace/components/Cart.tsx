import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CartItem } from '../types';

interface CartProps {
  isOpen: boolean;
  onClose: () => void;
  cartItems: CartItem[];
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
  onCheckout: () => void;
}

const CloseIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
);

const TrashIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
);


const Cart: React.FC<CartProps> = ({ isOpen, onClose, cartItems, onUpdateQuantity, onRemove, onCheckout }) => {

    const subtotal = cartItems.reduce((acc, item) => {
        const price = parseFloat(item.price.replace('₹', ''));
        return acc + price * item.quantity;
    }, 0);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/50 z-50"
                        aria-hidden="true"
                    />
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                        className="fixed top-0 right-0 w-full max-w-md h-full bg-brand-gray-light z-50 flex flex-col"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="cart-heading"
                    >
                        <header className="flex items-center justify-between p-4 border-b border-gray-200">
                            <h2 id="cart-heading" className="text-xl font-bold text-brand-brown-dark font-serif">Your Cart</h2>
                            <button onClick={onClose} className="p-1 rounded-full hover:bg-gray-200" aria-label="Close cart">
                                <CloseIcon />
                            </button>
                        </header>
                        
                        <div className="flex-1 overflow-y-auto p-4">
                            {cartItems.length === 0 ? (
                                <div className="text-center text-brand-gray h-full flex flex-col justify-center items-center">
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>
                                    <p className="text-lg">Your cart is empty</p>
                                    <p className="text-sm">Add some items to get started!</p>
                                </div>
                            ) : (
                                <ul className="space-y-4">
                                    {cartItems.map(item => (
                                        <li key={item.id} className="flex items-start gap-4 bg-white p-3 rounded-lg shadow-sm">
                                            <img src={item.imageUrl} alt={item.name} className="w-20 h-20 object-cover rounded-md" />
                                            <div className="flex-1">
                                                <h3 className="font-semibold text-brand-brown-dark">{item.name}</h3>
                                                <p className="text-sm text-brand-gray">{item.price}</p>
                                                <div className="flex items-center justify-between mt-2">
                                                    <div className="flex items-center border border-gray-200 rounded-md">
                                                        <button onClick={() => onUpdateQuantity(item.id, item.quantity - 1)} className="px-2 py-1 text-lg leading-none" aria-label={`Decrease quantity of ${item.name}`}>-</button>
                                                        <span className="px-2 py-1 text-sm">{item.quantity}</span>
                                                        <button onClick={() => onUpdateQuantity(item.id, item.quantity + 1)} className="px-2 py-1 text-lg leading-none" aria-label={`Increase quantity of ${item.name}`}>+</button>
                                                    </div>
                                                    <button onClick={() => onRemove(item.id)} className="text-gray-400 hover:text-red-500 transition-colors" aria-label={`Remove ${item.name} from cart`}>
                                                        <TrashIcon />
                                                    </button>
                                                </div>
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        {cartItems.length > 0 && (
                            <footer className="p-4 border-t border-gray-200 bg-white">
                                <div className="flex justify-between items-center mb-4 font-semibold">
                                    <span className="text-brand-gray">Subtotal</span>
                                    <span className="text-xl text-brand-brown-dark">₹{subtotal.toFixed(2)}</span>
                                </div>
                                <button 
                                    onClick={onCheckout}
                                    className="w-full bg-brand-green text-white font-bold py-3 px-6 rounded-full hover:bg-brand-green-dark transition-all duration-300"
                                >
                                    Proceed to Checkout
                                </button>
                            </footer>
                        )}
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
};

export default Cart;
