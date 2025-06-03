from openai import OpenAI
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AICommenter:
    def __init__(self, api_key: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        self.prompt_template = """
        You are a fitness and wellness expert creating engaging Instagram comments for fitness-related posts. 
        Write a friendly, authentic, and relevant comment for this fitness post.
        
        Post caption: "{caption}"
        
        Guidelines:
        - Keep it under 200 characters
        - Sound natural and human-like
        - Be positive and engaging
        - Ask a question or add value when possible
        - Don't use emojis in every comment
        - Vary your responses to sound natural
        - Focus on fitness/motivation aspects
        
        Comment types:
        1. Workout-related: Comment on exercises, intensity, or form
        2. Nutrition-related: Comment on meal prep or healthy eating
        3. Motivation: Encourage and support the poster
        4. Progress: Acknowledge visible progress
        
        Comment:"""
    
    def generate_comment(self, post_caption: str) -> str:
        """Generate a comment using OpenAI's API"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates engaging Instagram comments."},
                    {"role": "user", "content": self.prompt_template.format(caption=post_caption)}
                ],
                max_tokens=100,
                temperature=0.7,
            )
            
            comment = response.choices[0].message.content.strip()
            # Clean up the comment
            comment = comment.strip('"\'').strip()
            return comment
            
        except Exception as e:
            print(f"Error generating comment: {e}")
            # Fallback to a generic comment if API fails
            return "Great post! Thanks for sharing."
    
    def is_comment_appropriate(self, comment: str) -> bool:
        """Check if the generated comment is appropriate to post"""
        # Basic validation
        if not comment or len(comment) < 5 or len(comment) > 200:
            return False
            
        # Check for common issues
        blacklist = ['[', ']', 'as an AI', 'as a language model', 'I cannot', "I'm sorry"]
        if any(phrase.lower() in comment.lower() for phrase in blacklist):
            return False
            
        return True
