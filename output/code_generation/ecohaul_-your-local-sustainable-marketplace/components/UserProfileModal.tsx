import React, { useState } from 'react';
import Spinner from './Spinner';

interface UserProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: { name: string; email: string };
  token: string;
  onProfileUpdate: (name: string, email: string) => void;
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:3005';

const UserProfileModal: React.FC<UserProfileModalProps> = ({ isOpen, onClose, user, token, onProfileUpdate }) => {
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  React.useEffect(() => {
    if (isOpen) {
      setName(user.name);
      setEmail(user.email);
      setPassword('');
      setError(null);
      setSuccess(false);
    }
  }, [isOpen, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError(null); setSuccess(false);
    try {
      const res = await fetch(`${BACKEND_URL}/api/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name, email, password: password || undefined })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Update failed');
      setSuccess(true);
      onProfileUpdate(name, email);
      setTimeout(() => { setSuccess(false); onClose(); }, 1200);
    } catch (err: any) {
      setError(err.message);
    } finally { setLoading(false); }
  };

  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-lg p-8 w-full max-w-sm relative">
        <button onClick={onClose} className="absolute top-2 right-2 text-gray-400 hover:text-red-500">✕</button>
        <h2 className="text-2xl font-bold mb-4 text-brand-green-dark text-center">My Profile</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full border rounded p-2" required placeholder="Name" />
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full border rounded p-2" required placeholder="Email" />
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full border rounded p-2" placeholder="New Password (optional)" />
          {error && <div className="text-red-600 text-sm text-center">{error}</div>}
          {success && <div className="text-green-600 text-sm text-center">Profile updated!</div>}
          <button type="submit" className="w-full bg-brand-green text-white py-2 rounded font-bold" disabled={loading}>
            {loading ? <Spinner size={20} className="inline-block align-middle" /> : 'Save Changes'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default UserProfileModal; 