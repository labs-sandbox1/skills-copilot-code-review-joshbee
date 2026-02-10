"""
In-Memory database configuration and setup for Mergington High School API
"""

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from typing import Dict, Any, List, Optional
import copy


class InMemoryCollection:
    """Simple in-memory collection that mimics MongoDB operations"""
    
    def __init__(self):
        self.data: Dict[str, Dict[str, Any]] = {}
    
    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching the query"""
        if "_id" in query:
            doc = self.data.get(query["_id"])
            return copy.deepcopy(doc) if doc else None
        
        # For other queries, return first match
        for key, doc in self.data.items():
            if self._matches_query(doc, query):
                result = copy.deepcopy(doc)
                result["_id"] = key
                return result
        return None
    
    def find(self, query: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Find all documents matching the query"""
        if query is None or not query:
            return [{"_id": k, **copy.deepcopy(v)} for k, v in self.data.items()]
        
        results = []
        for key, doc in self.data.items():
            if self._matches_query(doc, query):
                result = copy.deepcopy(doc)
                result["_id"] = key
                results.append(result)
        return results
    
    def insert_one(self, document: Dict[str, Any]):
        """Insert a single document"""
        doc_id = document.pop("_id")
        self.data[doc_id] = copy.deepcopy(document)
    
    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        """Update a single document"""
        class UpdateResult:
            def __init__(self, modified):
                self.modified_count = modified
        
        if "_id" in query:
            doc_id = query["_id"]
            if doc_id in self.data:
                if "$push" in update:
                    for field, value in update["$push"].items():
                        if field not in self.data[doc_id]:
                            self.data[doc_id][field] = []
                        self.data[doc_id][field].append(value)
                if "$pull" in update:
                    for field, value in update["$pull"].items():
                        if field in self.data[doc_id] and value in self.data[doc_id][field]:
                            self.data[doc_id][field].remove(value)
                if "$set" in update:
                    for field, value in update["$set"].items():
                        self.data[doc_id][field] = value
                return UpdateResult(1)
        return UpdateResult(0)
    
    def delete_one(self, query: Dict[str, Any]):
        """Delete a single document"""
        class DeleteResult:
            def __init__(self, deleted):
                self.deleted_count = deleted
        
        if "_id" in query:
            doc_id = query["_id"]
            if doc_id in self.data:
                del self.data[doc_id]
                return DeleteResult(1)
        return DeleteResult(0)
    
    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simple aggregation pipeline support"""
        results = []
        
        # Handle $unwind -> $group -> $sort pattern for getting unique days
        if len(pipeline) >= 2 and "$unwind" in pipeline[0] and "$group" in pipeline[1]:
            unique_values = set()
            field = pipeline[0]["$unwind"].replace("$", "")
            
            for doc in self.data.values():
                # Navigate nested fields
                value = doc
                for part in field.split("."):
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                
                if isinstance(value, list):
                    unique_values.update(value)
            
            results = [{"_id": val} for val in sorted(unique_values)]
        
        return results
    
    def count_documents(self, query: Dict[str, Any]) -> int:
        """Count documents matching the query"""
        return len(self.data)
    
    def _matches_query(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """Check if document matches query"""
        for key, value in query.items():
            if key.startswith("$"):
                continue
            
            # Handle nested fields
            doc_value = doc
            for part in key.split("."):
                if isinstance(doc_value, dict):
                    doc_value = doc_value.get(part)
                else:
                    return False
            
            # Handle operators
            if isinstance(value, dict):
                if "$in" in value:
                    if not isinstance(doc_value, list):
                        return False
                    if not any(v in doc_value for v in value["$in"]):
                        return False
                if "$gte" in value:
                    if doc_value < value["$gte"]:
                        return False
                if "$lte" in value:
                    if doc_value > value["$lte"]:
                        return False
            elif doc_value != value:
                return False
        
        return True


# Create in-memory collections
activities_collection = InMemoryCollection()
teachers_collection = InMemoryCollection()
announcements_collection = InMemoryCollection()

# Methods


def hash_password(password):
    """Hash password using Argon2"""
    ph = PasswordHasher()
    return ph.hash(password)


def verify_password(hashed_password: str, plain_password: str) -> bool:
    """Verify a plain password against an Argon2 hashed password.

    Returns True when the password matches, False otherwise.
    """
    ph = PasswordHasher()
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except argon2_exceptions.VerifyMismatchError:
        return False
    except Exception:
        # For any other exception (e.g., invalid hash), treat as non-match
        return False


def init_database():
    """Initialize database if empty"""

    # Initialize activities if empty
    if activities_collection.count_documents({}) == 0:
        for name, details in initial_activities.items():
            activities_collection.insert_one({"_id": name, **details})

    # Initialize teacher accounts if empty
    if teachers_collection.count_documents({}) == 0:
        for teacher in initial_teachers:
            teachers_collection.insert_one(
                {"_id": teacher["username"], **teacher})

    # Initialize announcements if empty
    if announcements_collection.count_documents({}) == 0:
        for announcement in initial_announcements:
            announcements_collection.insert_one(announcement)


# Initial database if empty
initial_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Mondays and Fridays, 3:15 PM - 4:45 PM",
        "schedule_details": {
            "days": ["Monday", "Friday"],
            "start_time": "15:15",
            "end_time": "16:45"
        },
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 7:00 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "07:00",
            "end_time": "08:00"
        },
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Morning Fitness": {
        "description": "Early morning physical training and exercises",
        "schedule": "Mondays, Wednesdays, Fridays, 6:30 AM - 7:45 AM",
        "schedule_details": {
            "days": ["Monday", "Wednesday", "Friday"],
            "start_time": "06:30",
            "end_time": "07:45"
        },
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Tuesday", "Thursday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and compete in basketball tournaments",
        "schedule": "Wednesdays and Fridays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Wednesday", "Friday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore various art techniques and create masterpieces",
        "schedule": "Thursdays, 3:15 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Thursday"],
            "start_time": "15:15",
            "end_time": "17:00"
        },
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Monday", "Wednesday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and prepare for math competitions",
        "schedule": "Tuesdays, 7:15 AM - 8:00 AM",
        "schedule_details": {
            "days": ["Tuesday"],
            "start_time": "07:15",
            "end_time": "08:00"
        },
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 3:30 PM - 5:30 PM",
        "schedule_details": {
            "days": ["Friday"],
            "start_time": "15:30",
            "end_time": "17:30"
        },
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "amelia@mergington.edu"]
    },
    "Weekend Robotics Workshop": {
        "description": "Build and program robots in our state-of-the-art workshop",
        "schedule": "Saturdays, 10:00 AM - 2:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "10:00",
            "end_time": "14:00"
        },
        "max_participants": 15,
        "participants": ["ethan@mergington.edu", "oliver@mergington.edu"]
    },
    "Science Olympiad": {
        "description": "Weekend science competition preparation for regional and state events",
        "schedule": "Saturdays, 1:00 PM - 4:00 PM",
        "schedule_details": {
            "days": ["Saturday"],
            "start_time": "13:00",
            "end_time": "16:00"
        },
        "max_participants": 18,
        "participants": ["isabella@mergington.edu", "lucas@mergington.edu"]
    },
    "Sunday Chess Tournament": {
        "description": "Weekly tournament for serious chess players with rankings",
        "schedule": "Sundays, 2:00 PM - 5:00 PM",
        "schedule_details": {
            "days": ["Sunday"],
            "start_time": "14:00",
            "end_time": "17:00"
        },
        "max_participants": 16,
        "participants": ["william@mergington.edu", "jacob@mergington.edu"]
    }
}

initial_teachers = [
    {
        "username": "mrodriguez",
        "display_name": "Ms. Rodriguez",
        "password": hash_password("art123"),
        "role": "teacher"
    },
    {
        "username": "mchen",
        "display_name": "Mr. Chen",
        "password": hash_password("chess456"),
        "role": "teacher"
    },
    {
        "username": "principal",
        "display_name": "Principal Martinez",
        "password": hash_password("admin789"),
        "role": "admin"
    }
]

initial_announcements = [
    {
        "_id": "1",
        "message": "Activity registration is open until the end of the month. Don't lose your spot!",
        "start_date": "2026-02-01",
        "expiration_date": "2026-02-28",
        "created_by": "principal",
        "created_at": "2026-02-01T09:00:00"
    },
    {
        "_id": "2",
        "message": "Spring break is coming! No activities scheduled from March 15-22.",
        "start_date": "2026-02-15",
        "expiration_date": "2026-03-14",
        "created_by": "principal",
        "created_at": "2026-02-05T10:30:00"
    }
]
