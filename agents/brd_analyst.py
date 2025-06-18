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
from .models import BRDRequirementsAnalysis, BrdAnalysisInput
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
            message_bus=message_bus
        )
        
        # Simplified initialization - no longer need custom parser
        self._initialize_prompt_templates()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
    
    def _initialize_prompt_templates(self):
        """
        Initializes a single, comprehensive prompt template for the agent.
        The {format_instructions} are now automatically provided by the Pydantic parser
        in the base agent's execute_llm_chain method.
        """
        # New consolidated prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=(
                "You are an expert Business Requirements Document (BRD) Analyst. Your task is to perform a "
                "comprehensive analysis of the provided BRD and structure the output precisely according to the "
                "provided JSON schema. Do not add any text or explanation outside of the final JSON object."
            )),
            HumanMessage(content="""
                Please analyze the following Business Requirements Document:

                --- BRD CONTENT START ---
                {brd_content}
                --- BRD CONTENT END ---

                Based on the document, perform a full analysis and extract the following information:
                1.  **Project Overview:** A concise project name, summary, and list of primary business goals.
                2.  **Requirements:** A detailed list of all functional and non-functional requirements. Each requirement must have a unique ID, a title, a clear description, a category (e.g., 'functional', 'non-functional'), and a priority ('high', 'medium', 'low').
                3.  **Constraints, Assumptions, and Risks:** Identify any project constraints, key assumptions made, and potential risks.
                4.  **Target Audience and Business Context:** Identify the intended users and business context.
                5.  **Gap & Quality Analysis:** Assess the BRD for missing information, ambiguities, and overall quality. Provide scores from 1-10 for completeness, clarity, consistency, and testability, and include recommendations for improvement.

                CRITICAL: You must use the JSON format provided in the format instructions below.
                {format_instructions}
            """)
        ])
        
    def run(self, raw_brd: str) -> Dict[str, Any]:
        """
        Analyzes a BRD using a single, robust, structured call to the LLM.

        Args:
            raw_brd: The raw text content of the BRD.

        Returns:
            A dictionary conforming to the BRDRequirementsAnalysis schema.
        """
        try:
            # Enhanced logging to help debug BRD analysis issues
            self.log_start(f"Starting structured BRD analysis (content length: {len(raw_brd)})")
            self.logger.info(f"BRD content preview (first 100 chars): {raw_brd[:100]}...")
            
            # Check for common issues with the BRD
            if len(raw_brd) < 100:
                self.log_warning(f"BRD content is suspiciously short ({len(raw_brd)} chars). This may affect analysis quality.")
            
            start_time = time.time()
            input_data = BrdAnalysisInput(raw_brd=raw_brd)

            # Use the new, robust execute_llm_chain with a Pydantic model
            self.logger.info("Executing LLM chain to analyze BRD...")
            analysis_result = self.execute_llm_chain(
                inputs={"brd_content": input_data.raw_brd},
                output_pydantic_model=BRDRequirementsAnalysis,  # Key to structured output
                max_retries=2,
                additional_llm_params={"max_tokens": 8192}
            )
            
            # Additional validation of the result
            if analysis_result:
                self.logger.info(f"Analysis completed. Project name: '{analysis_result.get('project_name', 'Unknown')}'")
                self.logger.info(f"Requirements extracted: {len(analysis_result.get('requirements', []))}")
            else:
                self.logger.error("Analysis result is empty or invalid")

            duration = time.time() - start_time
            self.log_success(f"BRD analysis completed successfully in {duration:.2f}s.")
            self.log_execution_summary(analysis_result)
            return analysis_result

        except Exception as e:
            self.logger.error(f"A critical error occurred during BRD analysis: {str(e)}", exc_info=True)
            monitoring.log_agent_activity(
                self.agent_name,
                f"Failed to analyze BRD: {str(e)}",
                "ERROR"
            )
            return self.get_default_response()
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
            }
        )
        self.log_warning("Using default BRD analysis response due to processing failure.")
        return default_response.dict()
        
    def log_execution_summary(self, result: Dict[str, Any]) -> None:
        """Logs a summary of the execution results."""
        if not result or result.get("project_name") == "Analysis Failed - Please check logs":
            self.log_warning("Cannot log execution summary: result is empty or default.")
            return

        req_count = len(result.get("requirements", []))
        quality = result.get("quality_assessment", {})
        quality_score = quality.get("overall_quality_score", "N/A")
        
        summary_msg = f"Analyzed '{result.get('project_name')}': Extracted {req_count} requirements. Overall quality score: {quality_score}/10."
        monitoring.log_agent_activity(self.agent_name, summary_msg, "SUCCESS")
        self.logger.info(summary_msg)

    def log_execution_summary(self, result: Dict[str, Any]) -> None:
        """Logs a summary of the execution results."""
        if not result or result.get("project_name") == "Untitled Project":
            self.log_warning("Cannot log execution summary: result is empty or default.")
            return

        req_count = len(result.get("requirements", []))
        quality = result.get("quality_assessment", {})
        quality_score = quality.get("overall_quality_score", "N/A")
        
        summary_msg = f"Analyzed '{result.get('project_name')}': Extracted {req_count} requirements. Overall quality score: {quality_score}/10."
        monitoring.log_agent_activity(self.agent_name, summary_msg, "SUCCESS")
        self.logger.info(summary_msg)

