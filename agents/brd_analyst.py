import json
import re
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from config import get_gemini_model

class BRDAnalystAgent:
    def __init__(self, llm, memory):
        self.llm = llm # Gemini GenerativeModel instance
        self.memory = memory # SharedProjectMemory instance
    
    def sanitize_json(self, raw_json):
        """Apply multiple fixes to make sure JSON is valid."""
        # 1. Remove markdown code block fences
        if "```json" in raw_json:
            raw_json = raw_json.replace("```json", "")
        if "```" in raw_json:
            raw_json = raw_json.replace("```", "")
        raw_json = raw_json.strip()
        
        # 2. Parse line by line to fix common issues (this is more robust than regex)
        lines = raw_json.split('\n')
        fixed_lines = []
        in_array = False
        array_field = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
            
            # Check if we're entering an array
            if '"' in line and ':' in line and '[' in line and not ']' in line:
                field_name = line.split(':', 1)[0].strip().strip('"')
                in_array = True
                array_field = field_name
                fixed_lines.append(line)
                continue
                
            # Check if we're exiting an array incorrectly
            if in_array and '"' in line and ':' in line and '[' in line:
                # We found a new field without closing the previous array
                in_array = False
                # Insert closing bracket before this line
                fixed_lines.append("],")
                fixed_lines.append(line)
                continue
            
            # Fix missing comma after array item with a quote
            if in_array and line.endswith('"') and i < len(lines)-1 and '"' in lines[i+1] and not lines[i+1].strip().startswith(']'):
                fixed_lines.append(f"{line},")
                continue
            
            # Fix line that should end array but doesn't have closing bracket
            if in_array and '"' in line and i < len(lines)-1 and ('"' in lines[i+1] and ':' in lines[i+1]):
                in_array = False
                fixed_lines.append(f"{line}")
                fixed_lines.append("],")
                continue
                
            # Normal line
            fixed_lines.append(line)
        
        # Make sure we close any open arrays at the end
        if in_array:
            fixed_lines.append("]")
            
        fixed_json = '\n'.join(fixed_lines)
        
        # 3. Direct fixes for common patterns
        # Fix the specific issue with functional_requirements missing closing bracket
        patterns = [
            # Fix missing array closing bracket before new field
            (r'(\"\s*)",\s*"([a-zA-Z_]+)":', r'\1"],\n    "\2":'),
            
            # Fix double commas
            (r',\s*,', r','),
            
            # Fix trailing comma in array
            (r',\s*]', r']'),
        ]
        
        for pattern, replacement in patterns:
            fixed_json = re.sub(pattern, replacement, fixed_json)
        
        return fixed_json

    def run(self, raw_brd: str) -> dict:
        """
        Analyzes the raw BRD and extracts structured requirements.
        """
        print("BRD Analyst Agent: Analyzing raw BRD...")

        prompt = f"""
        You are an expert Business Requirements Document (BRD) Analyst AI.
        Your task is to thoroughly analyze the provided BRD, extract all key information, and present it in a structured JSON format.

        Focus on:
        1.  **High-Level Summary:** A concise overview of the project.
        2.  **Functional Requirements (FRs):** List each distinct functional requirement. If not explicitly numbered, infer them.
        3.  **Non-Functional Requirements (NFRs):** List all non-functional requirements (performance, security, scalability, usability, etc.).
        4.  **User Stories:** Convert identified functional requirements into standard "As a [type of user], I want to [goal] so that [reason/benefit]" format.
        5.  **Assumptions:** List any explicit or implicit assumptions made in the BRD.
        6.  **Potential Ambiguities/Questions:** Identify any parts of the BRD that are unclear, missing information, or could lead to different interpretations. If found, list them as questions for clarification.

        --- BRD ---
        {raw_brd}
        --- END BRD ---

        Output your analysis in this exact JSON format, with no other text:

        {{
            "summary": "string", 
            "functional_requirements": [
                "FR1: string",
                "FR2: string"
            ],
            "non_functional_requirements": [
                "NFR1: string",
                "NFR2: string"
            ],
            "user_stories": [
                "As a user, I want to...",
                "As a user, I want to..."
            ],
            "assumptions": [
                "string",
                "string"
            ],
            "ambiguities_or_questions": [
                "Question 1: string", 
                "Question 2: string"
            ]
        }}
        """

        try:
            # Call Gemini API
            response = self.llm.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1
                },
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )

            raw_json_output = response.text
            
            # Apply our comprehensive sanitization
            fixed_json = self.sanitize_json(raw_json_output)
            
            # Try to manually parse specific issue as a last resort
            try:
                parsed_data = json.loads(fixed_json)
            except json.JSONDecodeError as e:
                print(f"JSON decode error after sanitization: {e}")
                
                # Direct replacement of the known problematic pattern at char 1067
                if '"FR5:' in fixed_json and 'non_functional_requirements' in fixed_json:
                    # Explicitly locate and fix the transition between functional_requirements and non_functional_requirements
                    before = fixed_json.split('"non_functional_requirements"')[0]
                    if before.endswith('",'):
                        before = before[:-1] + '"],'
                    after = '"non_functional_requirements"' + fixed_json.split('"non_functional_requirements"')[1]
                    fixed_json = before + after
                
                try:
                    parsed_data = json.loads(fixed_json)
                except json.JSONDecodeError as e2:
                    print(f"Still couldn't parse JSON after specific fixes: {e2}")
                    print(f"Full problematic JSON:\n{fixed_json}")
                    
                    # Final fallback - let's manually construct a valid JSON
                    try:
                        manual_json = self._create_manual_json_fallback(raw_json_output)
                        parsed_data = json.loads(manual_json)
                    except Exception as e3:
                        print(f"All JSON parsing attempts failed: {e3}")
                        raise

            print("BRD Analyst Agent: Analysis complete.")
            return parsed_data

        except Exception as e:
            print(f"Error in BRD Analyst Agent: {e}")
            print(f"Problematic raw output (if any): {response.text if 'response' in locals() else 'No response object'}")
            raise
    
    def _create_manual_json_fallback(self, raw_text):
        """Emergency fallback that manually extracts sections and builds valid JSON"""
        # Define sections to look for
        sections = ["summary", "functional_requirements", "non_functional_requirements", 
                   "user_stories", "assumptions", "ambiguities_or_questions"]
        
        # Create a basic structure
        result = {}
        
        # Try to extract each section
        for section in sections:
            pattern = f'"{section}":\\s*\\[?\\s*"([^"]*)'
            match = re.search(pattern, raw_text)
            if match and section == "summary":
                result[section] = match.group(1).strip()
            else:
                # For array sections, try to extract all items
                items = []
                pattern = f'"{section}":\\s*\\[(.*?)\\]'
                match = re.search(pattern, raw_text, re.DOTALL)
                if match:
                    content = match.group(1)
                    # Extract items between quotes
                    item_pattern = r'"([^"]+)"'
                    items = re.findall(item_pattern, content)
                    
                # If we couldn't extract items properly, add a placeholder
                if not items and section != "summary":
                    if "FR" in raw_text and section == "functional_requirements":
                        fr_pattern = r'FR\d+:[^,"\]]*'
                        items = re.findall(fr_pattern, raw_text)
                    elif "NFR" in raw_text and section == "non_functional_requirements":
                        nfr_pattern = r'NFR\d+:[^,"\]]*'
                        items = re.findall(nfr_pattern, raw_text)
                    elif "As a" in raw_text and section == "user_stories":
                        story_pattern = r'As a [^,"\]]*'
                        items = re.findall(story_pattern, raw_text)
                
                # Default empty array if we couldn't extract anything
                result[section] = items if items else []
                
        # Convert to JSON
        return json.dumps(result)