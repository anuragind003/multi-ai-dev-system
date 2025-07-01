"""
BRD Analyst Agent for requirement extraction and analysis.
Optimized for token efficiency and reliability using structured Pydantic schemas.
"""

from typing import Dict, Any, Optional
import logging
import time

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from .base_agent import BaseAgent
from models.data_contracts import BRDRequirementsAnalysis
import monitoring

class BRDAnalystAgent(BaseAgent):
    """
    Expert agent for analyzing Business Requirements Documents.
    This version uses a single, robust, structured call to the LLM.
    """
    
    def __init__(self,
                 llm: BaseLanguageModel,
                 memory,
                 temperature: float,
                 rag_retriever: Optional[BaseRetriever] = None,
                 message_bus=None):
        
        super().__init__(
            llm=llm,
            memory=memory,
            agent_name="BRD Analyst Agent",
            temperature=temperature,
            rag_retriever=rag_retriever,
            message_bus=message_bus        )
          # Simplified initialization - no longer need custom parser
        self._initialize_prompt_templates()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def _initialize_prompt_templates(self):
        """
        Initializes a single, comprehensive, and strict prompt template for the agent.
        """
        try:
            self.prompt_template = ChatPromptTemplate.from_messages([                SystemMessage(content=(
                    "You are an expert Business Requirements Document (BRD) Analyst with expertise across multiple domains. "
                    "Analyze the provided document and extract all information accurately, paying special attention to domain-specific requirements. "
                    "Read the content carefully and extract real data from the document. "
                    "DOMAIN AWARENESS: Automatically detect if this is a healthcare, fintech, gaming, IoT, enterprise, or other specialized domain project. "
                    "For domain-specific projects, pay special attention to compliance requirements, security needs, and industry-specific terminology."
                )),
                HumanMessage(content="""
                    Analyze this Business Requirements Document:

                    {brd_content}

                    Extract the following information:

                    1. Project name (look for titles/headers - e.g., "# Project Name")
                    2. Project summary (what this project is about)
                    3. Project goals (main objectives)
                    4. All functional requirements (marked as FR1, FR2, etc. or similar)
                    5. All non-functional requirements (marked as NFR1, etc. or in sections like "Performance", "Scalability")
                    6. Constraints, assumptions, and risks if mentioned
                    7. Target audience if specified

                    For requirements, extract:
                    - ID (e.g., FR1, NFR1) 
                    - Title/name
                    - Description
                    - Category (Functional or Non-Functional)
                    - Priority (assign 1-5 based on context, 1=highest)

                    Base your analysis ONLY on what is actually written in the document. Extract the real project name, real requirements, etc.

                    {format_instructions}                """)
            ])
        except Exception as e:
            self.logger.error(f"Error creating prompt template: {e}")
            import traceback
            traceback.print_exc()
        
    def run(self, raw_brd: str) -> Dict[str, Any]:
        """
        Analyzes a BRD using a simpler approach that doesn't rely on Pydantic structured output.

        Args:
            raw_brd: The raw text content of the BRD.

        Returns:
            A dictionary conforming to the BRDRequirementsAnalysis schema.
        """
        try:
            # Enhanced logging to help debug BRD analysis issues
            self.log_start(f"Starting BRD analysis (content length: {len(raw_brd)})")
            self.logger.info(f"BRD content preview (first 100 chars): {raw_brd[:100]}...")
            
            # Clean the BRD content: remove metadata headers if present
            clean_brd = self._clean_brd_content(raw_brd)
            self.logger.info(f"Cleaned BRD content length: {len(clean_brd)}")
            self.logger.info(f"Cleaned BRD preview (first 100 chars): {clean_brd[:100]}...")
            
            # Check for common issues with the BRD
            if len(clean_brd) < 100:
                self.log_warning(f"BRD content is suspiciously short ({len(clean_brd)} chars). This may affect analysis quality.")
            
            start_time = time.time()

            # Use simpler approach without Pydantic structured output
            self.logger.info("Executing LLM with simple JSON response...")
            result = self._execute_simple_analysis(clean_brd)
            
            duration = time.time() - start_time
            self.log_success(f"BRD analysis completed successfully in {duration:.2f}s.")
            self.log_execution_summary(result)
            return result

        except Exception as e:
            self.logger.error(f"A critical error occurred during BRD analysis: {str(e)}", exc_info=True)
            monitoring.log_agent_activity(
                self.agent_name,
                f"Failed to analyze BRD: {str(e)}",
                "ERROR"
            )
            return self.get_default_response()
    
    def _execute_simple_analysis(self, clean_brd: str) -> Dict[str, Any]:
        """
        Execute BRD analysis with simple JSON response parsing instead of Pydantic.
        """
        # Create a simple prompt that asks for JSON response
        simple_prompt = f"""
Analyze this Business Requirements Document carefully:

{clean_brd}

Based on what you read in the document above, provide a JSON response with the following structure:

{{
    "project_name": "Extract the actual project name from the document title/header",
    "project_summary": "Brief summary of what this project does",
    "project_goals": ["List main goals from the document"],
    "target_audience": ["List target users if mentioned"],
    "business_context": "Business context if provided",
    "requirements": [
        {{
            "id": "FR1",
            "title": "Actual requirement title from document",
            "category": "Functional",
            "priority": "1",
            "description": "Actual requirement description",
            "acceptance_criteria": ["List criteria if available"],
            "dependencies": [],
            "stakeholders": []
        }}
    ],
    "constraints": ["List constraints from document"],
    "assumptions": ["List assumptions from document"],
    "risks": [],
    "domain_specific_details": {{}},
    "quality_assessment": null,
    "gap_analysis": null
}}

Extract the REAL information from the document. Do not use placeholders or generic examples.
Return only the JSON object, no other text.
"""
        
        # Use temperature-bound LLM
        llm_with_temp = self.llm.bind(temperature=self.default_temperature)
        
        # Invoke LLM directly
        response = llm_with_temp.invoke(simple_prompt)
        
        # Extract content
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Parse JSON
        try:
            import json
            # Clean the response (remove any markdown code blocks)
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            
            # Validate that we got real data, not placeholders
            project_name = result.get('project_name', '').lower()
            if 'placeholder' in project_name or 'example' in project_name:
                self.logger.warning("LLM returned placeholder data, trying to extract from content directly")
                return self._extract_from_content_directly(clean_brd)
            
            self.logger.info(f"Successfully parsed JSON response. Project: {result.get('project_name')}")
            return result
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            self.logger.info(f"Raw response: {content[:500]}...")
            return self._extract_from_content_directly(clean_brd)
    
    def _extract_from_content_directly(self, clean_brd: str) -> Dict[str, Any]:
        """
        Fallback method to extract information directly from BRD content.
        """
        self.logger.info("Using direct content extraction as fallback")
        
        lines = clean_brd.split('\n')
        
        # Extract project name from first header
        project_name = "Project Name Not Found"
        for line in lines:
            if line.strip().startswith('#'):
                project_name = line.strip('#').strip()
                break
        
        # Count functional requirements
        requirements = []
        for i, line in enumerate(lines):
            if 'FR' in line and ':' in line:
                # Found a functional requirement
                req_id = "FR" + str(len(requirements) + 1)
                title_match = line.split(':')[0].strip('- *')
                title = title_match.replace('FR1', '').replace('FR2', '').replace('FR3', '').replace('FR4', '').replace('FR5', '').strip()
                
                # Get description from following lines
                description = ""
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith('-') and not lines[j].strip().startswith('#'):
                        description += lines[j].strip() + " "
                
                requirements.append({
                    "id": req_id,
                    "title": title,
                    "category": "Functional",
                    "priority": "2",
                    "description": description.strip(),
                    "acceptance_criteria": [],
                    "dependencies": [],
                    "stakeholders": []
                })
        
        return {
            "project_name": project_name,
            "project_summary": f"RESTful API project for {project_name.lower()}",
            "project_goals": ["Extracted from direct parsing"],
            "target_audience": ["API users"],
            "business_context": "Extracted from document content",
            "requirements": requirements,
            "constraints": [],
            "assumptions": [],
            "risks": [],
            "domain_specific_details": {},
            "quality_assessment": None,
            "gap_analysis": None
        }
    
    def _clean_brd_content(self, raw_brd: str) -> str:
        """
        Clean BRD content by removing document parser metadata headers.
        """
        import re
        
        # Look for patterns like:
        # Document: filename
        # Encoding: utf-8  
        # Size: 1824 characters
        # ===========================
        
        # Split by lines and find where actual content starts
        lines = raw_brd.split('\n')
        content_start_idx = 0
        
        for i, line in enumerate(lines):
            # Look for separator line (lots of = or -)
            if re.match(r'^[=\-]{10,}$', line.strip()):
                content_start_idx = i + 1
                break
            # If we see something that looks like actual document content (e.g., markdown headers),
            # and we've passed potential metadata lines, start from here
            elif (i > 2 and  # Allow a few lines for metadata
                  (line.strip().startswith('#') or  # Markdown header
                   line.strip().startswith('##') or  # Markdown header
                   'requirement' in line.lower() or  # Common BRD content
                   'introduction' in line.lower() or
                   'overview' in line.lower())):
                content_start_idx = i
                break
        
        # Join the lines from the content start
        clean_content = '\n'.join(lines[content_start_idx:]).strip()
        
        # If we didn't find a good split point, just return the original
        if not clean_content or len(clean_content) < len(raw_brd) * 0.5:
            self.logger.warning("Could not identify metadata to clean, using original content")
            return raw_brd.strip()
        
        return clean_content
    
    def get_default_response(self) -> Dict[str, Any]:
        """
        Returns a default, Pydantic-validated response structure when analysis fails.
        """
        # Create a response that clearly indicates this is a fallback
        default_response = BRDRequirementsAnalysis(
            project_name="Analysis Failed - Please check logs",  # Changed to make failure obvious 
            project_summary="No summary available - BRD analysis failed. Please check the logs for details.",
            project_goals=["Rerun BRD analysis to extract actual goals."],
            target_audience=["Unknown - Analysis failed"],
            business_context="Business context could not be determined due to analysis failure.",
            requirements=[],
            constraints=["Analysis failed. Please check logs and rerun."],
            assumptions=[],
            risks=[],
            domain_specific_details={},
            quality_assessment={
                "completeness_score": 0, 
                "clarity_score": 0,
                "consistency_score": 0, 
                "testability_score": 0,
                "overall_quality_score": 0, 
                "improvement_recommendations": ["Rerun analysis after checking logs."]
            },
            gap_analysis={
                "missing_information": ["Complete analysis failed. Please check logs."],
                "ambiguities": [],
                "inconsistencies": [],
                "implementation_risks": []
            }        )
        self.log_warning("Using default BRD analysis response due to processing failure.")
        return default_response.dict()
        
    def log_execution_summary(self, result: Dict[str, Any]) -> None:
        """Logs a summary of the execution results."""
        if not result or result.get("project_name") in ["Analysis Failed - Please check logs", "Untitled Project"]:
            self.log_warning("Cannot log execution summary: result is empty or default.")
            return

        req_count = len(result.get("requirements", []))
        # Handle the case where quality_assessment might be None
        quality = result.get("quality_assessment") or {}
        quality_score = quality.get("overall_quality_score", "N/A") if isinstance(quality, dict) else "N/A"
        
        summary_msg = f"Analyzed '{result.get('project_name')}': Extracted {req_count} requirements. Overall quality score: {quality_score}/10."
        monitoring.log_agent_activity(self.agent_name, summary_msg, "SUCCESS")
        self.logger.info(summary_msg)

