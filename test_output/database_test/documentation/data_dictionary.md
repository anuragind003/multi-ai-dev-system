# Data Dictionary

## Table: users
| Column Name | Data Type | Constraints | Description |
|---|---|---|---|
| id | SERIAL | PRIMARY KEY | Unique identifier for each user |
| username | VARCHAR(255) | UNIQUE, NOT NULL | User's username |
| password | VARCHAR(255) | NOT NULL | User's password (encrypted) |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User's email address |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Timestamp indicating when the user was created |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | Timestamp indicating when the user was last updated |

## ... (Similar descriptions for other tables)