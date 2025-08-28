"""
Example script demonstrating LLM-powered code analysis
"""

import asyncio
import os
from src.llm_code_analyzer import LLMCodeAnalyzer

# Example code snippets for testing
sample_code_files = {
    "main.py": '''
import os
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import User, Task
from schemas import UserCreate, TaskCreate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Task Management API", version="1.0.0")

@app.post("/users/", response_model=dict)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user in the system"""
    try:
        db_user = User(name=user.name, email=user.email)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"Created user: {user.email}")
        return {"id": db_user.id, "message": "User created successfully"}
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=400, detail="Failed to create user")

@app.get("/users/{user_id}/tasks")
async def get_user_tasks(user_id: int, db: Session = Depends(get_db)):
    """Retrieve all tasks for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tasks = db.query(Task).filter(Task.user_id == user_id).all()
    return {"user": user.name, "tasks": [{"id": t.id, "title": t.title, "completed": t.completed} for t in tasks]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
''',
    
    "database.py": '''
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tasks.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
''',

    "utils/data_processor.py": '''
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta

class DataProcessor:
    """Advanced data processing utility for analytics"""
    
    def __init__(self, cache_size: int = 1000):
        self.cache = {}
        self.cache_size = cache_size
        self.processing_stats = {"calls": 0, "cache_hits": 0}
    
    def process_time_series(self, data: List[Dict[str, Any]], 
                           time_column: str = "timestamp",
                           value_column: str = "value") -> pd.DataFrame:
        """
        Process time series data with smoothing and trend analysis
        
        Args:
            data: List of data points with timestamps
            time_column: Name of timestamp column
            value_column: Name of value column
            
        Returns:
            Processed DataFrame with additional metrics
        """
        cache_key = f"ts_{hash(str(data))}"
        self.processing_stats["calls"] += 1
        
        if cache_key in self.cache:
            self.processing_stats["cache_hits"] += 1
            return self.cache[cache_key]
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        df[time_column] = pd.to_datetime(df[time_column])
        df = df.sort_values(time_column)
        
        # Add rolling averages
        df["moving_avg_7"] = df[value_column].rolling(window=7, min_periods=1).mean()
        df["moving_avg_30"] = df[value_column].rolling(window=30, min_periods=1).mean()
        
        # Calculate trends
        df["trend"] = df[value_column].pct_change().rolling(window=5).mean()
        
        # Detect anomalies using IQR method
        Q1 = df[value_column].quantile(0.25)
        Q3 = df[value_column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df["is_anomaly"] = (df[value_column] < lower_bound) | (df[value_column] > upper_bound)
        
        # Cache result
        if len(self.cache) >= self.cache_size:
            self.cache.clear()
        self.cache[cache_key] = df
        
        return df
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get processing performance statistics"""
        hit_rate = (self.processing_stats["cache_hits"] / 
                   max(self.processing_stats["calls"], 1)) * 100
        
        return {
            "total_calls": self.processing_stats["calls"],
            "cache_hits": self.processing_stats["cache_hits"],
            "cache_hit_rate": f"{hit_rate:.2f}%",
            "cache_size": len(self.cache)
        }
'''
}

async def demo_llm_analysis():
    """Demonstrate LLM-powered code analysis"""
    print("🤖 LLM Code Analysis Demo")
    print("=" * 50)
    
    # Check if OpenAI API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment variables")
        print("Set your OpenAI API key to run this demo:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Initialize LLM analyzer
    print("🔧 Initializing LLM Code Analyzer...")
    analyzer = LLMCodeAnalyzer(api_key=api_key, model="gpt-3.5-turbo")
    
    try:
        # Analyze the sample code
        print("🔍 Analyzing sample code files...")
        explanations = await analyzer.analyze_codebase(sample_code_files)
        
        # Display results
        print(f"\n✅ Analysis complete! Processed {len(explanations)} files:")
        print("-" * 50)
        
        for file_path, explanation in explanations.items():
            print(f"\n📁 {file_path}")
            print(f"   Language: {explanation.language}")
            print(f"   Complexity: {explanation.complexity_assessment}")
            print(f"   Summary: {explanation.summary}")
            
            if explanation.key_components:
                print(f"   Key Components:")
                for component in explanation.key_components[:3]:  # Show first 3
                    print(f"     • {component}")
            
            if explanation.improvement_suggestions:
                print(f"   AI Suggestions:")
                for suggestion in explanation.improvement_suggestions[:2]:  # Show first 2
                    print(f"     💡 {suggestion}")
        
        # Generate insights
        print(f"\n📊 Generating Code Insights...")
        insights = analyzer.generate_code_insights_summary(explanations)
        
        print(f"\n🎯 Key Insights:")
        print(f"   • Files Analyzed: {insights['total_files_analyzed']}")
        print(f"   • Complexity Distribution: {insights['complexity_distribution']}")
        print(f"   • Common Patterns: {', '.join(insights['common_patterns'][:3])}")
        print(f"   • Key Technologies: {', '.join(insights['key_technologies'][:5])}")
        
        if insights['improvement_themes']:
            print(f"   • Improvement Themes: {', '.join(insights['improvement_themes'])}")
    
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        print("This might be due to:")
        print("  • Invalid API key")
        print("  • Rate limit exceeded")
        print("  • Network connectivity issues")

def sync_demo():
    """Synchronous wrapper for the demo"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(demo_llm_analysis())

if __name__ == "__main__":
    sync_demo()
