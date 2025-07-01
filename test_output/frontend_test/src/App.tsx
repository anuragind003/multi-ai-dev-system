import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { ProductsPage } from './pages/ProductsPage';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import {ErrorBoundary} from './components/error/ErrorBoundary';

function App() {
  return (
    <Router>
      <ErrorBoundary fallback={<div>Something went wrong.</div>}>
        <div className="min-h-screen flex flex-col">
          <Header />
          <main className="flex-grow">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/products" element={<ProductsPage />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </ErrorBoundary>
    </Router>
  );
}

export default App;