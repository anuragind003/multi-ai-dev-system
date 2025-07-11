import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [message, setMessage] = useState('Loading...');
  const [backendHealth, setBackendHealth] = useState('Checking...');
  const [newItemName, setNewItemName] = useState('');
  const [newItemPrice, setNewItemPrice] = useState('');
  const [createdItem, setCreatedItem] = useState(null);
  const [fetchItemId, setFetchItemId] = useState('');
  const [fetchedItem, setFetchedItem] = useState(null);
  const [fetchError, setFetchError] = useState(null);

  const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

  useEffect(() => {
    // Fetch a simple message from the backend
    fetch(`${backendUrl}/api/health`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => setBackendHealth(data.message))
      .catch(error => {
        console.error("Error fetching backend health:", error);
        setBackendHealth(`Error: ${error.message}`);
      });

    setMessage('Welcome to the React Frontend!');
  }, [backendUrl]);

  const handleCreateItem = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/items/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newItemName,
          description: `Description for ${newItemName}`,
          price: parseFloat(newItemPrice),
          tax: 0.1 * parseFloat(newItemPrice),
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setCreatedItem(data.item);
      setNewItemName('');
      setNewItemPrice('');
    } catch (error) {
      console.error("Error creating item:", error);
      setCreatedItem({ error: `Failed to create item: ${error.message}` });
    }
  };

  const handleFetchItem = async () => {
    try {
      setFetchError(null);
      const response = await fetch(`${backendUrl}/api/items/${fetchItemId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setFetchedItem(data);
    } catch (error) {
      console.error("Error fetching item:", error);
      setFetchError(`Failed to fetch item: ${error.message}`);
      setFetchedItem(null);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>{message}</h1>
        <p>Backend Health: {backendHealth}</p>

        <div className="section">
          <h2>Create New Item</h2>
          <input
            type="text"
            placeholder="Item Name"
            value={newItemName}
            onChange={(e) => setNewItemName(e.target.value)}
          />
          <input
            type="number"
            placeholder="Item Price"
            value={newItemPrice}
            onChange={(e) => setNewItemPrice(e.target.value)}
          />
          <button onClick={handleCreateItem}>Create Item</button>
          {createdItem && (
            <p>Created: {createdItem.error ? createdItem.error : `${createdItem.name} ($${createdItem.price})`}</p>
          )}
        </div>

        <div className="section">
          <h2>Fetch Item by ID</h2>
          <input
            type="number"
            placeholder="Item ID (e.g., 1, 2, 3)"
            value={fetchItemId}
            onChange={(e) => setFetchItemId(e.target.value)}
          />
          <button onClick={handleFetchItem}>Fetch Item</button>
          {fetchedItem && (
            <p>Fetched: {fetchedItem.name} (ID: {fetchedItem.item_id}, Price: ${fetchedItem.price})</p>
          )}
          {fetchError && <p style={{ color: 'red' }}>{fetchError}</p>}
        </div>

        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          Learn React
        </a>
      </header>
    </div>
  );
}

export default App;