import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Header from './components/Header';
import Footer from './components/Footer';
import ProductCard from './components/ProductCard';
import ChatWidget from './components/ChatWidget';
import ProductSkeleton from './components/ProductSkeleton';
import Cart from './components/Cart';
import CheckoutSuccessModal from './components/CheckoutSuccessModal';
import { Product, CartItem } from './types';
import { generateProducts } from './services/geminiService';
import { fallbackProducts } from './data/fallbackData';
import ChooseIcon from './components/icons/ChooseIcon';
import PackageIcon from './components/icons/PackageIcon';
import DeliveryIcon from './components/icons/DeliveryIcon';
import Toast, { ToastType } from './components/Toast';
import Spinner from './components/Spinner';
import AdminDashboard from './components/AdminDashboard';
import VendorDashboard from './components/VendorDashboard';
import UserProfileModal from './components/UserProfileModal';

// --- Auth Modal Component ---
type AuthModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onLogin: (email: string, password: string) => void;
  onRegister: (name: string, email: string, password: string) => void;
  error: string | null;
  isLoading: boolean;
};
const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onLogin, onRegister, error, isLoading }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (!isOpen) {
      setName(''); setEmail(''); setPassword(''); setIsLogin(true);
    }
  }, [isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLogin) onLogin(email, password);
    else onRegister(name, email, password);
  };

  // Focus trap and ESC to close
  const modalRef = React.useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>('input,button');
        if (focusable.length) {
          e.preventDefault();
          focusable[0].focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);
  useEffect(() => {
    if (isOpen && modalRef.current) {
      const firstInput = modalRef.current.querySelector<HTMLElement>('input,button');
      firstInput?.focus();
    }
  }, [isOpen]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div ref={modalRef} className="bg-white rounded-lg shadow-lg p-8 w-full max-w-sm relative">
        <button onClick={onClose} className="absolute top-2 right-2 text-gray-400 hover:text-red-500">✕</button>
        <h2 className="text-2xl font-bold mb-4 text-brand-green-dark text-center">{isLogin ? 'Login' : 'Register'}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <input type="text" placeholder="Name" value={name} onChange={e => setName(e.target.value)} className="w-full border rounded p-2" required />
          )}
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} className="w-full border rounded p-2" required />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} className="w-full border rounded p-2" required />
          {error && <div className="text-red-600 text-sm text-center">{error}</div>}
          <button type="submit" className="w-full bg-brand-green text-white py-2 rounded font-bold" disabled={isLoading}>
            {isLoading ? <Spinner size={20} className="inline-block align-middle" /> : isLogin ? 'Login' : 'Register'}
          </button>
        </form>
        <div className="text-center mt-4">
          <button onClick={() => setIsLogin(!isLogin)} className="text-brand-green-dark underline">
            {isLogin ? "Don't have an account? Register" : 'Already have an account? Login'}
          </button>
        </div>
      </div>
    </div>
  );
};

// --- Order History Modal ---
type OrderHistoryModalProps = {
  isOpen: boolean;
  onClose: () => void;
  orders: any[];
  isLoading: boolean;
  error: string | null;
};
const OrderHistoryModal: React.FC<OrderHistoryModalProps> = ({ isOpen, onClose, orders, isLoading, error }) => {
  // Focus trap and ESC to close
  const modalRef = React.useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll<HTMLElement>('button');
        if (focusable.length) {
          e.preventDefault();
          focusable[0].focus();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);
  useEffect(() => {
    if (isOpen && modalRef.current) {
      const firstBtn = modalRef.current.querySelector<HTMLElement>('button');
      firstBtn?.focus();
    }
  }, [isOpen]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center">
      <div ref={modalRef} className="bg-white rounded-lg shadow-lg p-8 w-full max-w-lg relative">
        <button onClick={onClose} className="absolute top-2 right-2 text-gray-400 hover:text-red-500">✕</button>
        <h2 className="text-2xl font-bold mb-4 text-brand-green-dark text-center">Order History</h2>
        {isLoading ? <div className="flex justify-center py-8"><Spinner size={32} /></div> : error ? <div className="text-red-600">{error}</div> : (
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {orders.length === 0 ? <div className="text-center text-brand-gray">No orders yet.</div> : orders.map(order => (
              <div key={order.id} className="border rounded p-4">
                <div className="font-bold">Order #{order.id}</div>
                <div>Total: ₹{order.total_amount}</div>
                <div>Status: {order.status}</div>
                <div>Date: {new Date(order.created_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const MotionSection: React.FC<{ children: React.ReactNode; id?: string; className?: string }> = ({ children, id, className }) => (
    <motion.section
        id={id}
        className={className}
        initial={{ opacity: 0, y: 50 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.2 }}
        transition={{ duration: 0.6 }}
    >
        {children}
    </motion.section>
);


const InfoCard: React.FC<{ icon: React.ReactNode; title: string; description: string }> = ({ icon, title, description }) => (
    <div className="bg-white p-6 rounded-lg shadow-md text-center transform hover:-translate-y-1 transition-transform duration-300 group">
        <div className="flex justify-center items-center h-20 w-20 mx-auto bg-brand-green-light rounded-full mb-4 transition-all duration-300 group-hover:bg-brand-green group-hover:scale-110">
            {icon}
        </div>
        <h3 className="text-xl font-bold text-brand-brown-dark mb-2">{title}</h3>
        <p className="text-brand-gray">{description}</p>
    </div>
);


const App: React.FC = () => {
    const [products, setProducts] = useState<Product[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [cartItems, setCartItems] = useState<CartItem[]>([]);
    const [isCartOpen, setIsCartOpen] = useState(false);
    const [isCheckoutSuccess, setIsCheckoutSuccess] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [user, setUser] = useState<{ id: string; name: string; email: string; role: string } | null>(null);
    const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
    const [authModalOpen, setAuthModalOpen] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);
    const [authLoading, setAuthLoading] = useState(false);
    const [orderModalOpen, setOrderModalOpen] = useState(false);
    const [orders, setOrders] = useState<any[]>([]);
    const [ordersLoading, setOrdersLoading] = useState(false);
    const [ordersError, setOrdersError] = useState<string | null>(null);
    const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null);
    const showToast = (message: string, type: ToastType = 'info') => setToast({ message, type });
    const [adminDashboardOpen, setAdminDashboardOpen] = useState(false);
    const [vendorDashboardOpen, setVendorDashboardOpen] = useState(false);
    const [profileModalOpen, setProfileModalOpen] = useState(false);


    const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:3005';

    // --- Auth Logic ---
    const fetchMe = async (jwt?: string) => {
      if (!jwt) return setUser(null);
      try {
        const res = await fetch(`${BACKEND_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${jwt}` },
        });
        if (!res.ok) throw new Error('Failed to fetch user');
        const data = await res.json();
        setUser(data);
      } catch {
        setUser(null);
      }
    };
    useEffect(() => { if (token) fetchMe(token); }, [token]);

    const handleLogin = async (email: string, password: string) => {
      setAuthLoading(true); setAuthError(null);
      try {
        const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Login failed');
        setToken(data.token); localStorage.setItem('token', data.token);
        setUser(data.user); setAuthModalOpen(false);
        showToast('Login successful!', 'success');
      } catch (err: any) {
        setAuthError(err.message);
        showToast(err.message, 'error');
      } finally { setAuthLoading(false); }
    };
    const handleRegister = async (name: string, email: string, password: string) => {
      setAuthLoading(true); setAuthError(null);
      try {
        const res = await fetch(`${BACKEND_URL}/api/auth/register`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Registration failed');
        // Auto-login after register
        await handleLogin(email, password);
        showToast('Registration successful!', 'success');
      } catch (err: any) {
        setAuthError(err.message);
        showToast(err.message, 'error');
      } finally { setAuthLoading(false); }
    };
    // --- Cart Backend Sync ---
    const fetchCart = async (jwt: string) => {
      try {
        const res = await fetch(`${BACKEND_URL}/api/carts`, {
          headers: { Authorization: `Bearer ${jwt}` },
        });
        if (!res.ok) throw new Error('Failed to fetch cart');
        const backendCart = await res.json();
        // Map backend cart to CartItem[]
        setCartItems(backendCart.map((item: any) => ({
          id: item.product_id.toString(),
          name: item.name || '',
          price: item.price ? `₹${item.price}` : '',
          imageUrl: item.image || '',
          category: item.category || '',
          tags: [],
          vendor: '',
          quantity: item.quantity,
        })));
      } catch {
        setCartItems([]);
      }
    };

    // Fetch cart on login
    useEffect(() => {
      if (user && token) fetchCart(token);
      else setCartItems([]);
      // eslint-disable-next-line
    }, [user, token]);

    const handleAddToCart = async (productToAdd: Product) => {
      if (user && token) {
        // Check if already in cart
        const existing = cartItems.find(item => item.id === productToAdd.id);
        if (existing) {
          // Update quantity
          const cartItem = cartItems.find(item => item.id === productToAdd.id);
          if (cartItem) {
            const res = await fetch(`${BACKEND_URL}/api/carts/${cartItem.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
              body: JSON.stringify({ user_id: user.id, product_id: productToAdd.id, quantity: cartItem.quantity + 1 })
            });
            if (res.ok) fetchCart(token);
          }
        } else {
          // Add new
          const res = await fetch(`${BACKEND_URL}/api/carts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ user_id: user.id, product_id: productToAdd.id, quantity: 1 })
          });
          if (res.ok) fetchCart(token);
        }
      } else {
        setCartItems(prevItems => {
          const existingItem = prevItems.find(item => item.id === productToAdd.id);
          if (existingItem) {
            return prevItems.map(item =>
              item.id === productToAdd.id
                ? { ...item, quantity: item.quantity + 1 }
                : item
            );
          }
          return [...prevItems, { ...productToAdd, quantity: 1 }];
        });
      }
    };

    const handleUpdateCartQuantity = async (productId: string, quantity: number) => {
      if (user && token) {
        const cartItem = cartItems.find(item => item.id === productId);
        if (!cartItem) return;
        if (quantity <= 0) {
          // Remove from backend
          await fetch(`${BACKEND_URL}/api/carts/${productId}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` },
          });
          fetchCart(token);
        } else {
          await fetch(`${BACKEND_URL}/api/carts/${productId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            body: JSON.stringify({ user_id: user.id, product_id: productId, quantity })
          });
          fetchCart(token);
        }
      } else {
        setCartItems(prevItems => {
          if (quantity <= 0) {
            return prevItems.filter(item => item.id !== productId);
          }
          return prevItems.map(item =>
            item.id === productId ? { ...item, quantity } : item
          );
        });
      }
    };

    const handleRemoveFromCart = async (productId: string) => {
      if (user && token) {
        await fetch(`${BACKEND_URL}/api/carts/${productId}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` },
        });
        fetchCart(token);
      } else {
        setCartItems(prevItems => prevItems.filter(item => item.id !== productId));
      }
    };

    // On logout, clear cart
    const handleLogout = () => {
      setUser(null); setToken(null); localStorage.removeItem('token');
      setCartItems([]);
      showToast('Logged out successfully.', 'info');
    };

    const loadProducts = async () => {
        setIsLoading(true);
        setIsGenerating(true);
        setError(null);
        try {
            const response = await fetch(`${BACKEND_URL}/api/products`);
            if (!response.ok) throw new Error('Failed to fetch products from backend');
            const backendProducts = await response.json();
            // Map backend fields to frontend Product type
            const fetchedProducts: Product[] = backendProducts.map((p: any) => ({
                id: p.id.toString(),
                name: p.name,
                vendor: p.vendor || '', // backend doesn't have vendor yet
                price: p.price ? `₹${p.price}` : '',
                imageUrl: p.image || '',
                category: p.category || '',
                tags: p.tags || [],
            }));
            setProducts(fetchedProducts);
        } catch (err) {
            console.error("Primary product fetch failed, loading fallback data.", err);
            setError("We couldn't load products from the backend. Here's a look at our classic collection!");
            setProducts(fallbackProducts);
            if (err instanceof Error) {
                console.error(err.message);
            }
        } finally {
            setIsLoading(false);
            setIsGenerating(false);
        }
    };

    useEffect(() => {
        loadProducts();
    }, []);

    // --- Checkout Logic ---
    const handleCheckout = async () => {
      if (!user || !token) {
        setAuthModalOpen(true);
        return;
      }
      if(cartItems.length === 0) return;
      try {
        const res = await fetch(`${BACKEND_URL}/api/checkout`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error('Checkout failed');
        setIsCartOpen(false);
        setIsCheckoutSuccess(true);
        setCartItems([]);
        setTimeout(() => setIsCheckoutSuccess(false), 4000);
        showToast('Order placed successfully!', 'success');
      } catch (err) {
        showToast('Checkout failed. Please try again.', 'error');
      }
    };

    // --- Order History Logic ---
    const fetchOrders = async () => {
      if (!user || !token) {
        setAuthModalOpen(true);
        return;
      }
      setOrdersLoading(true); setOrdersError(null);
      try {
        const res = await fetch(`${BACKEND_URL}/api/orders`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to fetch orders');
        setOrders(data);
        setOrderModalOpen(true);
        showToast('Order history loaded.', 'info');
      } catch (err: any) {
        setOrdersError(err.message);
        showToast(err.message, 'error');
      } finally { setOrdersLoading(false); }
    };
    
    const cartCount = cartItems.reduce((total, item) => total + item.quantity, 0);

    const handleVendorApply = async () => {
      if (!token) return;
      try {
        const res = await fetch(`${BACKEND_URL}/api/vendor/apply`, {
          method: 'POST', headers: { Authorization: `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to apply');
        showToast('Vendor application submitted. Awaiting admin approval.', 'success');
        setUser(u => u ? { ...u, role: 'pending_vendor' } : u);
      } catch (err: any) {
        showToast(err.message, 'error');
      }
    };

    return (
        <div className="bg-brand-brown-light font-sans text-brand-gray-dark">
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
            <Header cartCount={cartCount} onCartClick={() => setIsCartOpen(true)} />
            <div className="container mx-auto px-6 py-2 flex justify-end items-center gap-4">
              {user ? (
                <>
                  <span className="text-brand-green-dark font-semibold">Hello, {user.name} <span className="text-xs text-brand-gray ml-2">[{user.role}]</span></span>
                  <button onClick={() => setProfileModalOpen(true)} className="bg-gray-200 text-brand-green-dark px-4 py-1 rounded-full font-semibold text-sm">My Profile</button>
                  {user.role === 'admin' && (
                    <button onClick={() => setAdminDashboardOpen(true)} className="bg-blue-700 text-white px-4 py-1 rounded-full font-semibold text-sm">Admin Dashboard</button>
                  )}
                  {user.role === 'vendor' && (
                    <button onClick={() => setVendorDashboardOpen(true)} className="bg-yellow-600 text-white px-4 py-1 rounded-full font-semibold text-sm">Vendor Dashboard</button>
                  )}
                  {user && user.role === 'user' && (
                    <button onClick={handleVendorApply} className="bg-yellow-500 text-white px-4 py-1 rounded-full font-semibold text-sm">Become a Vendor</button>
                  )}
                  {user && user.role === 'pending_vendor' && (
                    <span className="text-yellow-700 font-semibold ml-2">Vendor application pending approval</span>
                  )}
                  <button onClick={fetchOrders} className="bg-brand-green text-white px-4 py-1 rounded-full font-semibold text-sm">Order History</button>
                  <button onClick={handleLogout} className="bg-red-500 text-white px-4 py-1 rounded-full font-semibold text-sm">Logout</button>
                </>
              ) : (
                <button onClick={() => setAuthModalOpen(true)} className="bg-brand-green text-white px-4 py-1 rounded-full font-semibold text-sm">Login / Register</button>
              )}
            </div>
            <Cart 
              isOpen={isCartOpen} 
              onClose={() => setIsCartOpen(false)}
              cartItems={cartItems}
              onUpdateQuantity={handleUpdateCartQuantity}
              onRemove={handleRemoveFromCart}
              onCheckout={handleCheckout}
            />
            {isCheckoutSuccess && <CheckoutSuccessModal />}
            <AuthModal 
              isOpen={authModalOpen} 
              onClose={() => setAuthModalOpen(false)}
              onLogin={handleLogin}
              onRegister={handleRegister}
              error={authError}
              isLoading={authLoading}
            />
            <OrderHistoryModal 
              isOpen={orderModalOpen}
              onClose={() => setOrderModalOpen(false)}
              orders={orders}
              isLoading={ordersLoading}
              error={ordersError}
            />
            <UserProfileModal
              isOpen={profileModalOpen}
              onClose={() => setProfileModalOpen(false)}
              user={{ name: user?.name || '', email: user?.email || '' }}
              token={token || ''}
              onProfileUpdate={(name, email) => setUser(u => u ? { ...u, name, email } : u)}
            />
            {adminDashboardOpen && user?.role === 'admin' && <AdminDashboard onClose={() => setAdminDashboardOpen(false)} token={token!} />}
            {vendorDashboardOpen && user?.role === 'vendor' && <VendorDashboard onClose={() => setVendorDashboardOpen(false)} token={token!} />}


            <main>
                {/* Hero Section */}
                <section className="relative h-[60vh] md:h-[80vh] flex items-center justify-center text-white text-center px-4">
                    <div className="absolute inset-0 bg-black opacity-50 z-10"></div>
                    <img src="https://images.unsplash.com/photo-1542838132-92c53300491e?q=80&w=1974&auto=format&fit=crop" alt="Bustling local farmer's market with fresh produce" className="absolute inset-0 w-full h-full object-cover"/>
                    <div className="relative z-20">
                        <h1 className="text-4xl md:text-6xl font-bold font-serif mb-4 leading-tight" style={{textShadow: '0 2px 4px rgba(0,0,0,0.5)'}}>Goods that are Good for You & the Planet.</h1>
                        <p className="text-lg md:text-xl max-w-2xl mx-auto mb-8" style={{textShadow: '0 1px 3px rgba(0,0,0,0.4)'}}>Hyperlocal delivery of sustainable products from the best local creators in your neighborhood.</p>
                        <a href="#products" className="bg-brand-green text-white font-bold py-3 px-8 rounded-full text-lg hover:bg-brand-green-dark transition-all duration-300 transform hover:scale-105">
                            Start Shopping
                        </a>
                    </div>
                </section>

                {/* How It Works Section */}
                <MotionSection id="how-it-works" className="py-20 bg-white">
                    <div className="container mx-auto px-6 text-center">
                        <h2 className="text-3xl font-bold text-brand-brown-dark font-serif mb-4">Effortless & Eco-Friendly</h2>
                        <p className="text-lg text-brand-gray max-w-3xl mx-auto mb-12">Bringing sustainability to your doorstep in three simple steps.</p>
                        <div className="grid md:grid-cols-3 gap-8">
                            <InfoCard 
                                icon={<ChooseIcon />}
                                title="1. Choose Your Goods"
                                description="Browse our curated selection of local, sustainable products from verified vendors."
                            />
                            <InfoCard 
                                icon={<PackageIcon />}
                                title="2. Sustainable Packing"
                                description="We use reusable and compostable packaging to ensure a minimal environmental footprint."
                            />
                            <InfoCard 
                                icon={<DeliveryIcon />}
                                title="3. Zero-Emission Delivery"
                                description="Your order arrives via our fleet of electric bikes, making every delivery clean and green."
                            />
                        </div>
                    </div>
                </MotionSection>
                
                {/* Featured Products Section */}
                <MotionSection id="products" className="py-20 bg-brand-brown-light">
                    <div className="container mx-auto px-6">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-brand-brown-dark font-serif mb-4">Featured Sustainable Goods</h2>
                            <p className="text-lg text-brand-gray max-w-3xl mx-auto mb-6">Fresh ideas for sustainable living, generated just for you. Don't like what you see? Get new ideas!</p>
                             <button 
                                onClick={loadProducts}
                                disabled={isGenerating}
                                className="bg-brand-green text-white font-bold py-2 px-6 rounded-full hover:bg-brand-green-dark transition-all duration-300 transform hover:scale-105 disabled:bg-gray-400 disabled:scale-100 disabled:cursor-not-allowed"
                            >
                                {isGenerating ? 'Generating...' : 'Refresh Ideas'}
                            </button>
                        </div>
                        
                        {error && (
                            <div className="text-center text-yellow-800 bg-yellow-100 p-4 rounded-lg border border-yellow-200 mb-8">
                                <p className="font-bold">{error}</p>
                            </div>
                        )}

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
                            {isLoading ? (
                                Array.from({ length: 6 }).map((_, i) => <div key={i} className="flex justify-center items-center h-64"><Spinner size={40} /></div>)
                            ) : (
                                products.map(product => (
                                    <ProductCard key={product.id} product={product} onAddToCart={handleAddToCart} />
                                ))
                            )}
                        </div>
                    </div>
                </MotionSection>

                {/* Our Mission Section */}
                <MotionSection id="mission" className="py-20 bg-white">
                    <div className="container mx-auto px-6">
                        <div className="flex flex-col lg:flex-row items-center gap-12">
                            <div className="lg:w-1/2">
                                <img src="https://images.unsplash.com/photo-1593113598332-cd288d649433?q=80&w=2070&auto=format&fit=crop" alt="Hands holding soil with a small green plant sprouting" className="rounded-lg shadow-lg w-full h-auto object-cover aspect-[4/3]" />
                            </div>
                            <div className="lg:w-1/2">
                                <span className="text-brand-green font-semibold">OUR PROMISE</span>
                                <h2 className="text-3xl font-bold text-brand-brown-dark font-serif mt-2 mb-4">Authenticity, Transparency, Trust</h2>
                                <p className="text-brand-gray mb-4">
                                    We're more than a delivery service; we're a community. We partner directly with local artisans and farmers who share our commitment to the planet.
                                </p>
                                <p className="text-brand-gray font-semibold mb-2">Our Vendor Vetting Process:</p>
                                <ul className="list-disc list-inside text-brand-gray space-y-2">
                                    <li><span className="font-semibold">Eco-Friendly Materials:</span> Products must be made from sustainable, recycled, or natural materials.</li>
                                    <li><span className="font-semibold">Ethical Practices:</span> We ensure fair labor practices and ethical sourcing for all our partners.</li>
                                    <li><span className="font-semibold">Local First:</span> We prioritize vendors within a 50km radius to keep our community thriving and emissions low.</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </MotionSection>
                
                {/* Vendor Call to Action */}
                <MotionSection id="vendors" className="py-20 bg-gradient-to-br from-brand-green-light to-lime-100">
                    <div className="container mx-auto px-6 text-center">
                        <h2 className="text-3xl font-bold text-brand-green-dark font-serif mb-4">Are You a Local Creator?</h2>
                        <p className="text-lg text-brand-gray-dark max-w-2xl mx-auto mb-8">Join our platform to reach conscious consumers in your community and grow your sustainable business.</p>
                        <button className="bg-white text-brand-green-dark font-bold py-3 px-8 rounded-full text-lg border-2 border-brand-green-dark hover:bg-brand-green-dark hover:text-white transition-all duration-300 transform hover:scale-105">
                            Partner With Us
                        </button>
                    </div>
                </MotionSection>
            </main>

            <Footer />
            <ChatWidget />
        </div>
    );
};

export default App;