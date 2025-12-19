"""
Profile loader for cached profiles.
Loads pre-ingested profiles and embeddings from the profile_cache directory.
"""

import json
import pickle
from pathlib import Path
from typing import Optional

from app.models.schemas import ProfileInput


class ProfileLoader:
    """Load profiles and embeddings from local cache."""

    def __init__(self) -> None:
        # Profile cache is located at the project root
        self.cache_dir = Path.cwd().parent.parent / "profile_cache"
        if not self.cache_dir.exists():
            self.cache_dir = Path.cwd() / "profile_cache"
        self.cache_dir.mkdir(exist_ok=True)

    def load_profile(self, profile_name: str) -> Optional[ProfileInput]:
        """Load a profile by name from cache."""
        profile_file = self.cache_dir / f"{profile_name}_profile.json"
        
        if not profile_file.exists():
            raise FileNotFoundError(f"Profile not found: {profile_name}")
        
        with open(profile_file) as f:
            profile_data = json.load(f)
        
        return ProfileInput(**profile_data)

    def load_embeddings(self, profile_name: str):
        """Load embeddings for a profile."""
        embeddings_file = self.cache_dir / f"{profile_name}_embeddings.pkl"
        
        if not embeddings_file.exists():
            raise FileNotFoundError(f"Embeddings not found for profile: {profile_name}")
        
        with open(embeddings_file, "rb") as f:
            return pickle.load(f)

    def list_profiles(self) -> list[str]:
        """List all available profiles."""
        profiles = []
        for metadata_file in self.cache_dir.glob("*_metadata.json"):
            profile_name = metadata_file.stem.replace("_metadata", "")
            profiles.append(profile_name)
        return sorted(profiles)

    def profile_exists(self, profile_name: str) -> bool:
        """Check if a profile exists."""
        profile_file = self.cache_dir / f"{profile_name}_profile.json"
        return profile_file.exists()
