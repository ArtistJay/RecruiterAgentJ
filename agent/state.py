from typing import TypedDict, List, Annotated
import operator


class AgentState(TypedDict):
    """Shared state flowing through the LangGraph pipeline."""
    
    # Input
    raw_jd: str
    
    # Configuration
    max_turns: int  # Upper limit for conversation turns (agent may stop early)
    
    # InParseGent output
    parsed_jd: dict
    
    # ScoutGent output
    matched_candidates: List[dict]
    
    # ConvoGent output
    engaged_candidates: List[dict]
    
    # FinalGent output
    final_shortlist: List[dict]
    
    # Running log
    logs: Annotated[List[str], operator.add]
