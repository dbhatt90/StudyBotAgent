"""Configuration and constants"""


class Config:
    """StudyBot configuration"""
    
    # Form schema
    FORM_SCHEMA = [
        {"Field Name": "Client", "Description": "Name of requester"},
        {"Field Name": "Problem", "Description": "What needs to be studied"},
        {"Field Name": "Discipline", "Description": "Scientific area"},
        {"Field Name": "Technique Area", "Description": "Specific technique"},
        {"Field Name": "Study Director", "Description": "Director name"},
        {"Field Name": "Study Director Site", "Description": "Lab location"},
        {"Field Name": "Priority", "Description": "Urgency level"},
        {"Field Name": "Date Results Required", "Description": "Deadline"},
        {"Field Name": "Sample Type", "Description": "Type of sample"},
        {"Field Name": "Sample ID", "Description": "Sample identifier"},
        {"Field Name": "Project Code", "Description": "Project code"},
        {"Field Name": "Special Instructions", "Description": "Special instructions"}
    ]
    
    # Conversation settings
    MAX_HISTORY = 50
    
    # Checkpoint settings
    CHECKPOINT_DIR = "checkpoints"
    
    # Greeting message
    GREETING = """👋 Hello! I'll help you create a study ticket.

💬 Tell me about your request - include details like:
• Your name
• What analysis you need
• How urgent it is
• Any other relevant information"""

