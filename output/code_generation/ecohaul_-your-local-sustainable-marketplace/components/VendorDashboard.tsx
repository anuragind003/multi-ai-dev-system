import React, { useEffect, useState } from 'react';
import Spinner from './Spinner';

interface VendorDashboardProps {
  onClose: () => void;
  token: string;
}

type Product = { id: number; name: string; price: number; category: string };
type Order = { id: number; user_id: number; total_amount: number; status: string; created_at: string };

const VendorDashboard: React.FC<VendorDashboardProps> = ({ onClose, token }) => {
  const [tab, setTab] = useState<'products' | 'orders'>('products');
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:3005';

  useEffect(() => {
    setError(null);
    setLoading(true);
    let url = '';
    if (tab === 'products') url = `${BACKEND_URL}/api/vendor/products`;
    if (tab === 'orders') url = `${BACKEND_URL}/api/vendor/orders`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.json())
      .then(data => {
        if (tab === 'products') setProducts(data);
        if (tab === 'orders') setOrders(data);
      })
      .catch(e => setError('Failed to load data'))
      .finally(() => setLoading(false));
  }, [tab, token]);

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-4xl relative">
        <button onClick={onClose} className="absolute top-2 right-2 text-gray-400 hover:text-red-500">✕</button>
        <h2 className="text-2xl font-bold mb-4 text-brand-green-dark text-center">Vendor Dashboard</h2>
        <div className="flex gap-4 mb-6 justify-center">
          <button onClick={() => setTab('products')} className={`px-4 py-2 rounded ${tab==='products'?'bg-brand-green text-white':'bg-gray-200'}`}>My Products</button>
          <button onClick={() => setTab('orders')} className={`px-4 py-2 rounded ${tab==='orders'?'bg-brand-green text-white':'bg-gray-200'}`}>My Orders</button>
        </div>
        {loading ? <div className="flex justify-center py-8"><Spinner size={32} /></div> : error ? <div className="text-red-600">{error}</div> : (
          <>
            {tab === 'products' && (
              <table className="w-full mb-4 text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-2 text-left">ID</th>
                    <th className="p-2 text-left">Name</th>
                    <th className="p-2 text-left">Category</th>
                    <th className="p-2 text-left">Price</th>
                    <th className="p-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(p => (
                    <tr key={p.id} className="border-b">
                      <td className="p-2">{p.id}</td>
                      <td className="p-2">{p.name}</td>
                      <td className="p-2">{p.category}</td>
                      <td className="p-2">₹{p.price}</td>
                      <td className="p-2 flex gap-2 justify-center">
                        <button className="text-blue-600 hover:underline">Edit</button>
                        <button className="text-red-600 hover:underline">Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {tab === 'orders' && (
              <table className="w-full mb-4 text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-2 text-left">ID</th>
                    <th className="p-2 text-left">User ID</th>
                    <th className="p-2 text-left">Total</th>
                    <th className="p-2 text-left">Status</th>
                    <th className="p-2 text-left">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(o => (
                    <tr key={o.id} className="border-b">
                      <td className="p-2">{o.id}</td>
                      <td className="p-2">{o.user_id}</td>
                      <td className="p-2">₹{o.total_amount}</td>
                      <td className="p-2">{o.status}</td>
                      <td className="p-2">{new Date(o.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default VendorDashboard; 