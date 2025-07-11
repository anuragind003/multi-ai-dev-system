import Head from 'next/head';
import { useState, useEffect } from 'react';

export default function Home() {
  const [backendMessage, setBackendMessage] = useState('Loading...');
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchBackendData = async () => {
      try {
        // Use environment variable for API base URL
        const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setBackendMessage(data.message);
      } catch (e) {
        console.error("Failed to fetch from backend:", e);
        setError(`Failed to connect to backend: ${e.message}. Is it running at ${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}?`);
        setBackendMessage('Error fetching from backend.');
      }
    };

    fetchBackendData();
  }, []);

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '20px', textAlign: 'center' }}>
      <Head>
        <title>Fullstack Application</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main>
        <h1>Welcome to the Fullstack Application!</h1>
        <p>This is the Next.js Frontend.</p>

        <div style={{ marginTop: '30px', padding: '20px', border: '1px solid #ccc', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
          <h2>Backend Status:</h2>
          {error ? (
            <p style={{ color: 'red', fontWeight: 'bold' }}>{error}</p>
          ) : (
            <p style={{ color: 'green', fontWeight: 'bold' }}>{backendMessage}</p>
          )}
        </div>

        <div style={{ marginTop: '40px' }}>
          <h3>Operational Information:</h3>
          <ul>
            <li><strong>Backend:</strong> FastAPI (Python)</li>
            <li><strong>Frontend:</strong> Next.js (React)</li>
            <li><strong>Containerization:</strong> Docker</li>
            <li><strong>CI/CD:</strong> GitHub Actions</li>
            <li><strong>Monitoring:</strong> Prometheus & Grafana</li>
            <li><strong>Deployment:</strong> Kubernetes</li>
          </ul>
        </div>
      </main>

      <footer style={{ marginTop: '50px', fontSize: '0.8em', color: '#666' }}>
        <p>&copy; {new Date().getFullYear()} DevOps Team. All rights reserved.</p>
      </footer>
    </div>
  );
}