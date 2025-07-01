# General Backend API Documentation

This document provides detailed information about the API endpoints and how to use them.

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. To access protected endpoints, you need to include a valid JWT in the `Authorization` header of your requests.

## Endpoints

### User Endpoints

- **POST /users/**: Create a new user
  - Request Body: `UserCreate` model
  - Response: `User` model

- **GET /users/{user_id}**: Get user by ID
  - Path Parameter: `user_id` (integer)
  - Response: `User` model

- **GET /users/**: List users with pagination
  - Query Parameters: `skip` (integer, default: 0), `limit` (integer, default: 100)
  - Response: List of `User` models

### Item Endpoints

- **POST /items/**: Create a new item
  - Request Body: `ItemCreate` model
  - Response: `Item` model

- **GET /items/{item_id}**: Get item by ID
  - Path Parameter: `item_id` (integer)
  - Response: `Item` model

- **GET /items/**: List items with pagination
  - Query Parameters: `skip` (integer, default: 0), `limit` (integer, default: 100)
  - Response: List of `Item` models

## Error Handling

The API follows the standard HTTP status codes for error handling. In case of an error, the response will include an `error` field with a description of the issue.

## Examples

You can find example requests and responses in the [examples](examples/) directory.
