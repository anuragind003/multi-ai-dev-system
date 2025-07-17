import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const CheckIcon = () => (
  <svg className="w-16 h-16 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <motion.path 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      strokeWidth={2} 
      d="M5 13l4 4L19 7"
      initial={{ pathLength: 0 }}
      animate={{ pathLength: 1 }}
      transition={{ duration: 0.5, ease: "easeInOut" }}
    />
  </svg>
);


const CheckoutSuccessModal: React.FC = () => {
  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        className="fixed inset-0 bg-brand-green/90 z-50 flex flex-col items-center justify-center text-white"
      >
        <motion.div
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
            className="flex flex-col items-center justify-center text-center p-8"
        >
          <div className="w-24 h-24 bg-white/20 rounded-full flex items-center justify-center mb-6">
            <CheckIcon />
          </div>
          <h2 className="text-3xl font-bold font-serif mb-2">Order Successful!</h2>
          <p className="text-lg">Thank you for your purchase. Your sustainable goods are on their way!</p>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default CheckoutSuccessModal;
