"""Field management and validation service"""

from typing import Dict, List


class FieldManager:
    """Manages form fields and progress tracking"""
    
    FORM_SCHEMA = [
        {"Field Name": "Client", "Description": "Name of requester"},
        {"Field Name": "Problem", "Description": "What needs to be studied"},
        {"Field Name": "Discipline", "Description": "Scientific area"},
        {"Field Name": "Technique Area", "Description": "Specific technique"},
        {"Field Name": "Study Director", "Description": "Director name"},
        {"Field Name": "Study Director Site", "Description": "Lab location"},
        {"Field Name": "Priority", "Description": "Urgency level"},
        {"Field Name": "Date Results Required", "Description": "Deadline for results"},
        {"Field Name": "Sample Type", "Description": "Type of sample"},
        {"Field Name": "Sample ID", "Description": "Unique sample identifier"},
        {"Field Name": "Project Code", "Description": "Project or cost center code"},
        {"Field Name": "Special Instructions", "Description": "Special handling instructions"}
    ]
    
    def __init__(self):
        """Initialize field manager with empty fields"""
        self.fields = {field["Field Name"]: None for field in self.FORM_SCHEMA}
    
    def update_fields(self, updates: Dict[str, str]) -> Dict[str, str]:
        """
        Update field values
        
        Args:
            updates: Dictionary of field_name -> value
            
        Returns:
            Dictionary of actually updated fields
        """
        updated = {}
        for field_name, value in updates.items():
            if field_name in self.fields:
                self.fields[field_name] = value
                updated[field_name] = value
                print(f"  📝 {field_name}: → {value}")
        return updated
    
    def get_field(self, field_name: str) -> str:
        """Get value of a specific field"""
        return self.fields.get(field_name)
    
    def get_filled_fields(self) -> Dict[str, str]:
        """Get all filled fields"""
        return {k: v for k, v in self.fields.items() if v}
    
    def get_empty_fields(self) -> List[str]:
        """Get list of unfilled field names"""
        return [k for k, v in self.fields.items() if not v]
    
    def calculate_progress(self) -> float:
        """
        Calculate completion percentage
        
        Returns:
            Progress percentage (0-100)
        """
        total = len(self.fields)
        filled = sum(1 for v in self.fields.values() if v)
        return round((filled / total) * 100, 1)
    
    def is_complete(self) -> bool:
        """Check if all fields are filled"""
        return all(self.fields.values())
    
    def validate_field(self, field_name: str, value: str) -> bool:
        """
        Validate a field value (extensible for custom validation)
        
        Args:
            field_name: Name of the field
            value: Value to validate
            
        Returns:
            True if valid
        """
        # Add custom validation logic here
        if field_name == "Priority" and value not in ["Low", "Medium", "High", "Critical"]:
            return False
        
        if not value or not value.strip():
            return False
        
        return True
    
    def get_schema(self) -> List[Dict]:
        """Get the form schema"""
        return self.FORM_SCHEMA
    
    def reset(self):
        """Reset all fields to None"""
        self.fields = {field["Field Name"]: None for field in self.FORM_SCHEMA}
    
    def to_dict(self) -> Dict:
        """Export fields as dictionary"""
        return self.fields.copy()
    
    def from_dict(self, data: Dict):
        """Import fields from dictionary"""
        for field_name, value in data.items():
            if field_name in self.fields:
                self.fields[field_name] = value

