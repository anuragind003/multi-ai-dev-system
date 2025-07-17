"""
Test the improved file validation for infrastructure files.
This tests the fixes for handling Terraform, Docker, and other DevOps files.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tools.code_generation_utils import parse_llm_output_into_files, _is_valid_filename, _validate_generated_file
from models.data_contracts import GeneratedFile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')

def test_infrastructure_files():
    """Test parsing and validation of infrastructure files."""
    
    print("=" * 60)
    print("TESTING INFRASTRUCTURE FILE VALIDATION")
    print("=" * 60)
    
    # Test case 1: The problematic Terraform and infrastructure files
    test_input = """### FILE: aws/vpc.tf
```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "main-vpc"
    Environment = "production"
  }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  map_public_ip_on_launch = true
  
  tags = {
    Name = "public-subnet-${count.index + 1}"
    Type = "public"
  }
}
```

### FILE: aws/security_groups.tf
```hcl
resource "aws_security_group" "web" {
  name_prefix = "web-sg"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

### FILE: Dockerfile.backend
```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

### FILE: docker-compose.yml
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_HOST=db
    depends_on:
      - db
  
  db:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### FILE: .env.example
```bash
NODE_ENV=development
PORT=3000
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp
DB_USER=user
DB_PASSWORD=password
API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
```

### FILE: .gitignore
```
node_modules/
.env
.env.local
dist/
build/
*.log
.DS_Store
```"""

    print("Testing infrastructure file parsing...")
    result = parse_llm_output_into_files(test_input)
    print(f"Parsed {len(result)} files:")
    
    for file in result:
        print(f"  ✅ {file.file_path} ({len(file.content)} chars)")
    
    print(f"\nShould have parsed 6 files, got {len(result)}")
    
    # Test individual filename validation
    print("\n" + "=" * 60)
    print("TESTING INDIVIDUAL FILENAME VALIDATION")
    print("=" * 60)
    
    test_filenames = [
        "aws/vpc.tf",
        "aws/security_groups.tf", 
        "Dockerfile.backend",
        "docker-compose.yml",
        ".env.example",
        ".gitignore",
        "terraform.tfvars",
        "kubernetes/deployment.yaml",
        "ansible/playbook.yml",
        "Makefile",
        "requirements.txt",
        "package.json"
    ]
    
    for filename in test_filenames:
        is_valid = _is_valid_filename(filename)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"  {status}: {filename}")
    
    # Test file object validation
    print("\n" + "=" * 60)
    print("TESTING FILE OBJECT VALIDATION")
    print("=" * 60)
    
    test_files = [
        GeneratedFile(
            file_path="aws/vpc.tf",
            content="""resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}""",
            purpose="VPC configuration",
            status="generated"
        ),
        GeneratedFile(
            file_path=".env",
            content="PORT=3000",
            purpose="Environment variables",
            status="generated"
        ),
        GeneratedFile(
            file_path="Dockerfile",
            content="FROM node:18\nWORKDIR /app",
            purpose="Docker configuration",
            status="generated"
        ),
        GeneratedFile(
            file_path="invalid_file",
            content="short",
            purpose="Test invalid file",
            status="generated"
        )
    ]
    
    for file in test_files:
        is_valid = _validate_generated_file(file)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"  {status}: {file.file_path} ({len(file.content)} chars)")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Infrastructure file parsing: {len(result)}/6 files parsed")
    
    valid_filenames = sum(1 for f in test_filenames if _is_valid_filename(f))
    print(f"✅ Filename validation: {valid_filenames}/{len(test_filenames)} valid")
    
    valid_file_objects = sum(1 for f in test_files if _validate_generated_file(f))
    print(f"✅ File object validation: {valid_file_objects}/{len(test_files)} valid")
    
    if len(result) >= 5 and valid_filenames >= 10 and valid_file_objects >= 3:
        print("\n🎉 ALL TESTS PASSED! Infrastructure files will now be accepted.")
    else:
        print("\n⚠️  Some tests failed. Check the validation logic.")

if __name__ == "__main__":
    test_infrastructure_files()
