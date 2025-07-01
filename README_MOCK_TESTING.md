# Mock Testing Setup for Code Generation

This document explains how to test the code generation agents using mock data that simulates the output from the plan compiler agent.

## Overview

The system works in a pipeline:

1. **BRD Analysis** → 2. **Tech Stack Recommendation** → 3. **System Design** → 4. **Plan Compilation** → 5. **Code Generation**

Since you mentioned the pipeline works fine till the **Plan Compiler Agent** (step 4), this mock setup allows you to test the **Code Generation** phase (step 5) in isolation.

## Files Created

### Test Scripts

- `test_code_generation.py` - Main test runner with mock data
- `test_architecture_generator.py` - Specific test for architecture generator
- `test_backend_generator.py` - Specific test for backend generator

### Mock Data Structure

The mock data simulates the output that would normally come from the plan compiler agent:

```json
{
  "brd_analysis": {
    "status": "success",
    "analysis_result": {
      "functional_requirements": [...],
      "non_functional_requirements": [...]
    }
  },
  "tech_stack": {
    "backend": {"language": "Python", "framework": "FastAPI"},
    "frontend": {"framework": "React", "language": "TypeScript"},
    "database": {"primary": "PostgreSQL", "cache": "Redis"}
  },
  "system_design": {
    "architecture_pattern": "Microservices",
    "data_models": [...],
    "api_design": {...}
  }
}
```

## How to Run Tests

### 1. Quick Mock Test

```bash
cd multi_ai_dev_system
python test_code_generation.py
```

This will:

- Load mock planning data
- Create a test output directory
- Save mock data for inspection
- Show next steps

### 2. Test Architecture Generator

```bash
python test_architecture_generator.py
```

This will:

- Use mock data to test the architecture generator
- Generate project structure files
- Save results to `test_output/architecture_test/`

### 3. Test Backend Generator

```bash
python test_backend_generator.py
```

This will:

- Use mock data to test the backend generator
- Generate backend code (models, APIs, services)
- Save results to `test_output/backend_test/`

## What Gets Generated

### Architecture Generator

- Project structure (directories, config files)
- Dockerfile and docker-compose.yml
- README.md and documentation
- Build scripts and deployment configs
- Base configuration files

### Backend Generator

- Data models (SQLAlchemy/ORM models)
- API routes and controllers
- Business logic services
- Configuration files
- Database connection setup
- Authentication/authorization components

### Expected Output Structure

```
test_output/
├── architecture_test/
│   ├── src/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
├── backend_test/
│   ├── models/
│   │   ├── user.py
│   │   ├── product.py
│   │   └── order.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── products.py
│   │   └── orders.py
│   └── services/
│       ├── user_service.py
│       └── product_service.py
└── mock_data.json
```

## Customizing Mock Data

You can modify the mock data in the test scripts to:

1. **Change tech stack**: Modify `mock_tech_stack` to test different frameworks
2. **Add more models**: Extend `data_models` array
3. **Add more endpoints**: Extend `api_design.endpoints` array
4. **Change requirements**: Modify functional/non-functional requirements

## Troubleshooting

### Common Issues

1. **Import Errors**

   - Ensure you're running from the `multi_ai_dev_system` directory
   - Check that all dependencies are installed

2. **LLM Configuration**

   - Ensure your LLM API keys are configured in `config.py`
   - Check that the LLM service is accessible

3. **Output Directory Permissions**
   - Ensure the script has write permissions for `test_output/`

### Debug Mode

To get more detailed output, modify the test scripts to enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Real Pipeline

Once you've verified the code generators work with mock data, you can:

1. **Replace Mock Data**: Use actual output from your plan compiler agent
2. **Test Full Pipeline**: Run the complete workflow from BRD to code generation
3. **Validate Generated Code**: Use the code execution tools to verify generated code compiles and runs

## Next Steps

1. Run the mock tests to verify code generation works
2. Check the generated files for quality and completeness
3. Modify mock data to test edge cases
4. Integrate with your actual plan compiler output
5. Test the complete pipeline end-to-end

## Example Usage

```bash
# 1. Test basic mock setup
python test_code_generation.py

# 2. Test architecture generation
python test_architecture_generator.py

# 3. Test backend generation
python test_backend_generator.py

# 4. Check results
ls -la test_output/
cat test_output/mock_data.json
```

This mock testing approach allows you to validate and debug the code generation phase independently of the planning phase, making development and testing much more efficient.
