import React, { useState } from 'react';
import { Product } from '../types';

interface ProductCardProps {
  product: Product;
  onAddToCart: (product: Product) => void;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, onAddToCart }) => {
  const [isAdded, setIsAdded] = useState(false);

  const handleAddToCartClick = () => {
    onAddToCart(product);
    setIsAdded(true);
    setTimeout(() => {
        setIsAdded(false);
    }, 2000);
  }

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden group transform hover:-translate-y-2 transition-transform duration-300 flex flex-col">
      <div className="relative">
        <img
          src={product.imageUrl}
          alt={product.name}
          className="w-full h-48 object-cover"
        />
        <div className="absolute top-2 left-2 bg-brand-green text-white text-xs font-bold px-2 py-1 rounded-full">
          {product.category}
        </div>
      </div>
      <div className="p-4 flex flex-col flex-grow">
        <h3 className="text-lg font-semibold text-brand-brown-dark mb-1">{product.name}</h3>
        <p className="text-sm text-brand-gray mb-2">by {product.vendor}</p>
        <div className="flex flex-wrap gap-1 mb-3">
          {product.tags.map((tag) => (
            <span key={tag} className="text-xs bg-brand-green-light text-brand-green-dark px-2 py-1 rounded-full">
              {tag}
            </span>
          ))}
        </div>
        <div className="flex justify-between items-center mt-auto pt-2">
          <p className="text-lg font-bold text-brand-green-dark">{product.price}</p>
          <button 
            onClick={handleAddToCartClick} 
            disabled={isAdded}
            className={`text-white px-4 py-2 rounded-full font-semibold text-sm transition-all duration-300 w-28 ${
                isAdded 
                ? 'bg-lime-500 cursor-not-allowed'
                : 'bg-brand-green hover:bg-brand-green-dark'
            }`}
          >
            {isAdded ? 'Added ✓' : 'Add to Cart'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;