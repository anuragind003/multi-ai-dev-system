import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { UATProvider } from './context/UATContext';
import HomePage from './pages/HomePage';
import TestCasesPage from './pages/TestCasesPage';
import TestRunPage from './pages/TestRunPage';
import NotFoundPage from './pages/NotFoundPage';
import Header from './components/Header';
import Footer from './components/Footer';

function App() {
  return (
    <UATProvider>
      <div className="flex flex-col min-h-screen bg-gray-100">
        <Header />
        <main className="flex-grow container mx-auto p-4">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/test-cases" element={<TestCasesPage />} />
            <Route path="/test-run/:testRunId" element={<TestRunPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </UATProvider>
  );
}

export default App;