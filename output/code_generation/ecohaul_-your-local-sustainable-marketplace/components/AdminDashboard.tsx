import React, { useEffect, useState } from 'react';
import Spinner from './Spinner';
import Toast from './Toast';

interface AdminDashboardProps {
  onClose: () => void;
  token: string;
}

type User = { id: number; name: string; email: string; role: string };
type Product = { id: number; name: string; price: number; category: string };
type Order = { id: number; user_id: number; total_amount: number; status: string; created_at: string };

const AdminDashboard: React.FC<AdminDashboardProps> = ({ onClose, token }) => {
  const [tab, setTab] = useState<'users' | 'products' | 'orders'>('users');
  const [users, setUsers] = useState<User[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => setToast({ message, type });

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:3005';

  useEffect(() => {
    setError(null);
    setLoading(true);
    let url = '';
    if (tab === 'users') url = `${BACKEND_URL}/api/admin/users`;
    if (tab === 'products') url = `${BACKEND_URL}/api/admin/products`;
    if (tab === 'orders') url = `${BACKEND_URL}/api/admin/orders`;
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(res => res.json())
      .then(data => {
        if (tab === 'users') setUsers(data);
        if (tab === 'products') setProducts(data);
        if (tab === 'orders') setOrders(data);
      })
      .catch(e => setError('Failed to load data'))
      .finally(() => setLoading(false));
  }, [tab, token]);

  const handleApprove = async (id: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/vendors/${id}/approve`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to approve');
      showToast('Vendor approved!', 'success');
      setUsers(users => users.map(u => u.id === id ? { ...u, role: 'vendor' } : u));
    } catch { showToast('Error approving vendor', 'error'); }
    setLoading(false);
  };
  const handleReject = async (id: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/admin/vendors/${id}/reject`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to reject');
      showToast('Vendor rejected.', 'info');
      setUsers(users => users.map(u => u.id === id ? { ...u, role: 'user' } : u));
    } catch { showToast('Error rejecting vendor', 'error'); }
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-4xl relative">
        <button onClick={onClose} className="absolute top-2 right-2 text-gray-400 hover:text-red-500">✕</button>
        <h2 className="text-2xl font-bold mb-4 text-brand-green-dark text-center">Admin Dashboard</h2>
        <div className="flex gap-4 mb-6 justify-center">
          <button onClick={() => setTab('users')} className={`px-4 py-2 rounded ${tab==='users'?'bg-brand-green text-white':'bg-gray-200'}`}>Users</button>
          <button onClick={() => setTab('products')} className={`px-4 py-2 rounded ${tab==='products'?'bg-brand-green text-white':'bg-gray-200'}`}>Products</button>
          <button onClick={() => setTab('orders')} className={`px-4 py-2 rounded ${tab==='orders'?'bg-brand-green text-white':'bg-gray-200'}`}>Orders</button>
        </div>
        {loading ? <div className="flex justify-center py-8"><Spinner size={32} /></div> : error ? <div className="text-red-600">{error}</div> : (
          <>
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
            {tab === 'users' && (
              <table className="w-full mb-4 text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-2 text-left">ID</th>
                    <th className="p-2 text-left">Name</th>
                    <th className="p-2 text-left">Email</th>
                    <th className="p-2 text-left">Role</th>
                    <th className="p-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id} className="border-b">
                      <td className="p-2">{u.id}</td>
                      <td className="p-2">{u.name}</td>
                      <td className="p-2">{u.email}</td>
                      <td className="p-2">{u.role}</td>
                      <td className="p-2 flex gap-2 justify-center">
                        <button className="text-blue-600 hover:underline">Edit</button>
                        <button className="text-red-600 hover:underline">Delete</button>
                        {u.role === 'pending_vendor' && (
                          <>
                            <button className="text-green-600 hover:underline" onClick={() => handleApprove(u.id)}>Approve</button>
                            <button className="text-yellow-600 hover:underline" onClick={() => handleReject(u.id)}>Reject</button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {tab === 'products' && (
              <table className="w-full mb-4 text-sm">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-2 text-left">ID</th>
                    <th className="p-2 text-left">Name</th>
                    <th className="p-2 text-left">Category</th>
                    <th className="p-2 text-left">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(p => (
                    <tr key={p.id} className="border-b">
                      <td className="p-2">{p.id}</td>
                      <td className="p-2">{p.name}</td>
                      <td className="p-2">{p.category}</td>
                      <td className="p-2">₹{p.price}</td>
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

export default AdminDashboard; 