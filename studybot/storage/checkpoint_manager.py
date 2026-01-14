"""Checkpoint persistence manager"""

import json
import os
from typing import Dict, Optional


class CheckpointManager:
    """Manages checkpoint persistence to disk"""
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        Initialize checkpoint manager
        
        Args:
            checkpoint_dir: Directory to store checkpoint files
        """
        self.checkpoint_dir = checkpoint_dir
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    def save(self, session_id: str, checkpoint_data: Dict) -> bool:
        """
        Save checkpoint to disk
        
        Args:
            session_id: Unique session identifier
            checkpoint_data: Dictionary containing session state
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = self._get_filepath(session_id)
            with open(filepath, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            print(f"💾 Checkpoint saved: {filepath}")
            return True
        except Exception as e:
            print(f"❌ Checkpoint save failed: {e}")
            return False
    
    def load(self, session_id: str) -> Optional[Dict]:
        """
        Load checkpoint from disk
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Checkpoint data if exists, None otherwise
        """
        try:
            filepath = self._get_filepath(session_id)
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    checkpoint = json.load(f)
                print(f"📂 Checkpoint loaded: {filepath}")
                return checkpoint
            return None
        except Exception as e:
            print(f"⚠️ Checkpoint load failed: {e}")
            return None
    
    def delete(self, session_id: str) -> bool:
        """
        Delete checkpoint file
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = self._get_filepath(session_id)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🗑️ Checkpoint deleted: {filepath}")
            return True
        except Exception as e:
            print(f"⚠️ Checkpoint delete failed: {e}")
            return False
    
    def exists(self, session_id: str) -> bool:
        """
        Check if checkpoint exists
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if checkpoint file exists
        """
        return os.path.exists(self._get_filepath(session_id))
    
    def list_checkpoints(self) -> list:
        """
        List all checkpoint files
        
        Returns:
            List of session IDs with checkpoints
        """
        try:
            files = os.listdir(self.checkpoint_dir)
            session_ids = [
                f.replace('checkpoint_', '').replace('.json', '')
                for f in files
                if f.startswith('checkpoint_') and f.endswith('.json')
            ]
            return session_ids
        except Exception as e:
            print(f"⚠️ Failed to list checkpoints: {e}")
            return []
    
    def _get_filepath(self, session_id: str) -> str:
        """Get full filepath for a session checkpoint"""
        return os.path.join(self.checkpoint_dir, f"checkpoint_{session_id}.json")