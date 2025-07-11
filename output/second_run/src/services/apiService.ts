const API_URL = 'https://api.example.com'; // Replace with your API URL

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: any;
}

const handleResponse = async (response: Response) => {
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
  }
  return response.json();
};

export const apiService = async (endpoint: string, options: RequestOptions = {}) => {
  const url = `${API_URL}${endpoint}`;
  const defaultHeaders = {
    'Content-Type': 'application/json',
  };

  const requestOptions: RequestOptions = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {}),
    },
  };

  if (requestOptions.body) {
    requestOptions.body = JSON.stringify(requestOptions.body);
  }

  try {
    const response = await fetch(url, requestOptions);
    return await handleResponse(response);
  } catch (error: any) {
    throw new Error(error.message || 'An unexpected error occurred.');
  }
};