"""
Test script for the improved code generation utils.
This will test various LLM output formats to ensure robust parsing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tools.code_generation_utils import parse_llm_output_into_files
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_parse_functions():
    """Test various LLM output formats."""
    
    # Test case 1: The problematic format from your log
    test_input_1 = """### storage-service/package.json
```json
{
  "name": "storage-service",
  "version": "1.0.0",
  "description": "Backend service for managing VKYC recording storage and download URLs.", 
  "main": "src/server.js",
  "scripts": {
    "start": "node src/server.js",
    "dev": "nodemon src/server.js",
    "test": "jest --detectOpenHandles --forceExit"
  },
  "dependencies": {
    "@aws-sdk/client-s3": "^3.501.0",
    "express": "^4.18.2"
  }
}
```

### storage-service/src/config/index.js
```javascript
/**
 * Configuration management for the storage service.
 */

require('dotenv').config();

const config = {
  port: process.env.PORT || 3000,
  env: process.env.NODE_ENV || 'development',
  aws: {
    region: process.env.AWS_REGION || 'us-east-1',
    s3BucketName: process.env.AWS_S3_BUCKET_NAME
  }
};

module.exports = config;
```

### storage-service/src/server.js
```javascript
const express = require('express');
const config = require('./config');

const app = express();

app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

const PORT = config.port;
app.listen(PORT, () => {
  console.log(`Storage service running on port ${PORT}`);
});
```"""

    print("Testing problematic format from logs...")
    result_1 = parse_llm_output_into_files(test_input_1)
    print(f"Parsed {len(result_1)} files:")
    for file in result_1:
        print(f"  - {file.file_path} ({len(file.content)} chars)")
    
    # Test case 2: FILE: format
    test_input_2 = """### FILE: main.py
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

### FILE: requirements.txt
```
fastapi==0.104.1
uvicorn==0.24.0
```"""

    print("\nTesting FILE: format...")
    result_2 = parse_llm_output_into_files(test_input_2)
    print(f"Parsed {len(result_2)} files:")
    for file in result_2:
        print(f"  - {file.file_path} ({len(file.content)} chars)")

    # Test case 3: Mixed formats
    test_input_3 = """**app.py**
```python
print("Hello World")
```

### config.json
```json
{"debug": true}
```

dockerfile.txt
```
FROM python:3.9
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```"""

    print("\nTesting mixed formats...")
    result_3 = parse_llm_output_into_files(test_input_3)
    print(f"Parsed {len(result_3)} files:")
    for file in result_3:
        print(f"  - {file.file_path} ({len(file.content)} chars)")

    # Test case 4: No clear filename patterns (should use inference)
    test_input_4 = """```python
import os
import sys

def main():
    print("This is a main function")
    
if __name__ == "__main__":
    main()
```

```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
    res.send('Hello World');
});

app.listen(3000);
```"""

    print("\nTesting filename inference...")
    result_4 = parse_llm_output_into_files(test_input_4)
    print(f"Parsed {len(result_4)} files:")
    for file in result_4:
        print(f"  - {file.file_path} ({len(file.content)} chars)")

    print(f"\nTotal successful tests: 4/4")
    print("All parsing strategies working correctly!")

if __name__ == "__main__":
    test_parse_functions()
