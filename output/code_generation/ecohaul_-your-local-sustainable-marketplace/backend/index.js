const express = require('express');
const app = express();
const cors = require('cors');
app.use(cors());
const PORT = process.env.PORT || 3005;
const db = require('./db');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const JWT_SECRET = process.env.JWT_SECRET || 'supersecretkey';

app.get('/api/hello', (req, res) => {
  res.json({ message: 'Hello from the backend!' });
});

// Product CRUD endpoints
app.get('/api/products', (req, res) => {
  db.all('SELECT * FROM products', [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

app.get('/api/products/:id', (req, res) => {
  db.get('SELECT * FROM products WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Product not found' });
    res.json(row);
  });
});

app.post('/api/products', express.json(), (req, res) => {
  const { name, description, price, image } = req.body;
  db.run(
    'INSERT INTO products (name, description, price, image) VALUES (?, ?, ?, ?)',
    [name, description, price, image],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      res.status(201).json({ id: this.lastID, name, description, price, image });
    }
  );
});

app.put('/api/products/:id', express.json(), (req, res) => {
  const { name, description, price, image } = req.body;
  db.run(
    'UPDATE products SET name = ?, description = ?, price = ?, image = ? WHERE id = ?',
    [name, description, price, image, req.params.id],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      if (this.changes === 0) return res.status(404).json({ error: 'Product not found' });
      res.json({ id: req.params.id, name, description, price, image });
    }
  );
});

app.delete('/api/products/:id', (req, res) => {
  db.run('DELETE FROM products WHERE id = ?', [req.params.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'Product not found' });
    res.json({ success: true });
  });
});

// User CRUD endpoints
app.get('/api/users', (req, res) => {
  db.all('SELECT id, name, email, role FROM users', [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

app.get('/api/users/:id', (req, res) => {
  db.get('SELECT id, name, email, role FROM users WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'User not found' });
    res.json(row);
  });
});

app.post('/api/users', express.json(), (req, res) => {
  const { name, email, password, role } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: 'Name, email, and password are required' });
  }
  db.run(
    'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
    [name, email, password, role || 'user'],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      res.status(201).json({ id: this.lastID, name, email, role: role || 'user' });
    }
  );
});

app.put('/api/users/:id', express.json(), (req, res) => {
  const { name, email, password, role } = req.body;
  db.run(
    'UPDATE users SET name = ?, email = ?, password = ?, role = ? WHERE id = ?',
    [name, email, password, role || 'user', req.params.id],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      if (this.changes === 0) return res.status(404).json({ error: 'User not found' });
      res.json({ id: req.params.id, name, email, role: role || 'user' });
    }
  );
});

app.delete('/api/users/:id', (req, res) => {
  db.run('DELETE FROM users WHERE id = ?', [req.params.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'User not found' });
    res.json({ success: true });
  });
});

// Cart CRUD endpoints
app.get('/api/carts', (req, res) => {
  db.all('SELECT * FROM carts', [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

app.get('/api/carts/:id', (req, res) => {
  db.get('SELECT * FROM carts WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Cart not found' });
    res.json(row);
  });
});

app.post('/api/carts', express.json(), (req, res) => {
  const { user_id, product_id, quantity } = req.body;
  if (!user_id || !product_id || !quantity) {
    return res.status(400).json({ error: 'user_id, product_id, and quantity are required' });
  }
  db.run(
    'INSERT INTO carts (user_id, product_id, quantity) VALUES (?, ?, ?)',
    [user_id, product_id, quantity],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      res.status(201).json({ id: this.lastID, user_id, product_id, quantity });
    }
  );
});

app.put('/api/carts/:id', express.json(), (req, res) => {
  const { user_id, product_id, quantity } = req.body;
  db.run(
    'UPDATE carts SET user_id = ?, product_id = ?, quantity = ? WHERE id = ?',
    [user_id, product_id, quantity, req.params.id],
    function (err) {
      if (err) return res.status(500).json({ error: err.message });
      if (this.changes === 0) return res.status(404).json({ error: 'Cart not found' });
      res.json({ id: req.params.id, user_id, product_id, quantity });
    }
  );
});

app.delete('/api/carts/:id', (req, res) => {
  db.run('DELETE FROM carts WHERE id = ?', [req.params.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'Cart not found' });
    res.json({ success: true });
  });
});

// Register endpoint
app.post('/api/auth/register', express.json(), async (req, res) => {
  const { name, email, password, role } = req.body;
  if (!name || !email || !password) {
    return res.status(400).json({ error: 'Name, email, and password are required' });
  }
  try {
    const hashedPassword = await bcrypt.hash(password, 10);
    db.run(
      'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
      [name, email, hashedPassword, role || 'user'],
      function (err) {
        if (err) return res.status(500).json({ error: err.message });
        res.status(201).json({ id: this.lastID, name, email, role: role || 'user' });
      }
    );
  } catch (err) {
    res.status(500).json({ error: 'Registration failed' });
  }
});

// Login endpoint
app.post('/api/auth/login', express.json(), (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password are required' });
  }
  db.get('SELECT * FROM users WHERE email = ?', [email], async (err, user) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!user) return res.status(401).json({ error: 'Invalid credentials' });
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(401).json({ error: 'Invalid credentials' });
    const token = jwt.sign({ id: user.id, email: user.email, role: user.role }, JWT_SECRET, { expiresIn: '1d' });
    res.json({ token, user: { id: user.id, name: user.name, email: user.email, role: user.role } });
  });
});

// JWT authentication middleware
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token provided' });
  jwt.verify(token, JWT_SECRET, (err, user) => {
    if (err) return res.status(403).json({ error: 'Invalid token' });
    req.user = user;
    next();
  });
}

// /api/auth/me endpoint
app.get('/api/auth/me', authenticateToken, (req, res) => {
  db.get('SELECT id, name, email, role FROM users WHERE id = ?', [req.user.id], (err, user) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!user) return res.status(404).json({ error: 'User not found' });
    res.json(user);
  });
});

// Update user profile (current user)
app.put('/api/profile', authenticateToken, express.json(), async (req, res) => {
  const { name, email, password } = req.body;
  if (!name || !email) {
    return res.status(400).json({ error: 'Name and email are required' });
  }
  let updateFields = [name, email];
  let query = 'UPDATE users SET name = ?, email = ?';
  if (password) {
    const hashedPassword = await bcrypt.hash(password, 10);
    query += ', password = ?';
    updateFields.push(hashedPassword);
  }
  query += ' WHERE id = ?';
  updateFields.push(req.user.id);
  db.run(query, updateFields, function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'User not found' });
    res.json({ success: true });
  });
});

// Role-based middleware
function requireRole(role) {
  return function (req, res, next) {
    if (!req.user || req.user.role !== role) {
      return res.status(403).json({ error: 'Forbidden: insufficient privileges' });
    }
    next();
  };
}

// --- Admin Endpoints ---
// List all users (admin only)
app.get('/api/admin/users', authenticateToken, requireRole('admin'), (req, res) => {
  db.all('SELECT id, name, email, role FROM users', [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});
// Update any user (admin only)
app.put('/api/admin/users/:id', authenticateToken, requireRole('admin'), express.json(), (req, res) => {
  const { name, email, role } = req.body;
  db.run('UPDATE users SET name = ?, email = ?, role = ? WHERE id = ?', [name, email, role, req.params.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'User not found' });
    res.json({ id: req.params.id, name, email, role });
  });
});
// Delete any user (admin only)
app.delete('/api/admin/users/:id', authenticateToken, requireRole('admin'), (req, res) => {
  db.run('DELETE FROM users WHERE id = ?', [req.params.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'User not found' });
    res.json({ success: true });
  });
});
// List all orders (admin only)
app.get('/api/admin/orders', authenticateToken, requireRole('admin'), (req, res) => {
  db.all('SELECT * FROM orders ORDER BY created_at DESC', [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});
// List all products (admin only)
app.get('/api/admin/products', authenticateToken, requireRole('admin'), (req, res) => {
  db.all('SELECT * FROM products', [], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});
// --- Vendor Endpoints ---
// List own products (vendor only)
app.get('/api/vendor/products', authenticateToken, requireRole('vendor'), (req, res) => {
  db.all('SELECT * FROM products WHERE vendor_id = ?', [req.user.id], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});
// Add product (vendor only)
app.post('/api/vendor/products', authenticateToken, requireRole('vendor'), express.json(), (req, res) => {
  const { name, description, price, image, category } = req.body;
  db.run('INSERT INTO products (name, description, price, image, category, vendor_id) VALUES (?, ?, ?, ?, ?, ?)', [name, description, price, image, category, req.user.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    res.status(201).json({ id: this.lastID, name, description, price, image, category, vendor_id: req.user.id });
  });
});
// List own orders (vendor only)
app.get('/api/vendor/orders', authenticateToken, requireRole('vendor'), (req, res) => {
  db.all('SELECT o.* FROM orders o JOIN order_items oi ON o.id = oi.order_id JOIN products p ON oi.product_id = p.id WHERE p.vendor_id = ? GROUP BY o.id ORDER BY o.created_at DESC', [req.user.id], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// Vendor registration (apply to become vendor)
app.post('/api/vendor/apply', authenticateToken, (req, res) => {
  // Only allow if not already vendor or pending
  db.get('SELECT role FROM users WHERE id = ?', [req.user.id], (err, user) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!user) return res.status(404).json({ error: 'User not found' });
    if (user.role === 'vendor' || user.role === 'pending_vendor') {
      return res.status(400).json({ error: 'Already a vendor or pending approval' });
    }
    db.run('UPDATE users SET role = ? WHERE id = ?', ['pending_vendor', req.user.id], function (err) {
      if (err) return res.status(500).json({ error: err.message });
      res.json({ success: true, message: 'Vendor application submitted. Awaiting admin approval.' });
    });
  });
});

// Admin: Approve or reject vendor
app.post('/api/admin/vendors/:id/approve', authenticateToken, requireRole('admin'), (req, res) => {
  db.run('UPDATE users SET role = ? WHERE id = ?', ['vendor', req.params.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'User not found' });
    res.json({ success: true });
  });
});
app.post('/api/admin/vendors/:id/reject', authenticateToken, requireRole('admin'), (req, res) => {
  db.run('UPDATE users SET role = ? WHERE id = ?', ['user', req.params.id], function (err) {
    if (err) return res.status(500).json({ error: err.message });
    if (this.changes === 0) return res.status(404).json({ error: 'User not found' });
    res.json({ success: true });
  });
});

// Orders table
const orderTable = `CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  total_amount REAL NOT NULL,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id)
);`;
const orderItemTable = `CREATE TABLE IF NOT EXISTS order_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  quantity INTEGER NOT NULL,
  price_at_purchase REAL NOT NULL,
  FOREIGN KEY(order_id) REFERENCES orders(id),
  FOREIGN KEY(product_id) REFERENCES products(id)
);`;
db.serialize(() => {
  db.run(orderTable);
  db.run(orderItemTable);
});

// POST /api/checkout - create order from user's cart
app.post('/api/checkout', authenticateToken, (req, res) => {
  const userId = req.user.id;
  db.all('SELECT * FROM carts WHERE user_id = ?', [userId], (err, cartItems) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!cartItems || cartItems.length === 0) return res.status(400).json({ error: 'Cart is empty' });
    // Calculate total
    db.all('SELECT id, price FROM products', [], (err, products) => {
      if (err) return res.status(500).json({ error: err.message });
      let total = 0;
      const itemsWithPrice = cartItems.map(item => {
        const product = products.find(p => p.id === item.product_id);
        const price = product ? product.price : 0;
        total += price * item.quantity;
        return { ...item, price };
      });
      db.run('INSERT INTO orders (user_id, total_amount) VALUES (?, ?)', [userId, total], function (err) {
        if (err) return res.status(500).json({ error: err.message });
        const orderId = this.lastID;
        // Insert order items
        const stmt = db.prepare('INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) VALUES (?, ?, ?, ?)');
        itemsWithPrice.forEach(item => {
          stmt.run(orderId, item.product_id, item.quantity, item.price);
        });
        stmt.finalize();
        // Clear user's cart
        db.run('DELETE FROM carts WHERE user_id = ?', [userId], err => {
          if (err) return res.status(500).json({ error: err.message });
          res.status(201).json({ orderId, total });
        });
      });
    });
  });
});

// GET /api/orders - get user's order history
app.get('/api/orders', authenticateToken, (req, res) => {
  const userId = req.user.id;
  db.all('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', [userId], (err, orders) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(orders);
  });
});

// User and Cart endpoints (stubs)
// TODO: Implement full CRUD for users and carts
app.get('/api/carts', (req, res) => res.json({ message: 'Cart list endpoint (to be implemented)' }));

const insertMockUsers = async () => {
  const users = [
    { name: 'Admin User', email: 'admin@ecohaul.com', password: 'adminpass', role: 'admin' },
    { name: 'Vendor User', email: 'vendor@ecohaul.com', password: 'vendorpass', role: 'vendor' },
    { name: 'Regular User', email: 'user@ecohaul.com', password: 'userpass', role: 'user' },
  ];
  for (const user of users) {
    db.get('SELECT * FROM users WHERE email = ?', [user.email], async (err, row) => {
      if (err) return;
      if (!row) {
        const hashedPassword = await bcrypt.hash(user.password, 10);
        db.run(
          'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
          [user.name, user.email, hashedPassword, user.role],
          (err) => {
            if (err) console.log('Error inserting mock user:', err.message);
          }
        );
      }
    });
  }
};

insertMockUsers();

app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
}); 