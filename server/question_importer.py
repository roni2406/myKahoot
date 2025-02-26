import pandas as pd
import json
from pathlib import Path
import base64
import os

class QuestionImporter:
    def __init__(self):
        self.required_columns = ['question', 'option_1', 'option_2', 'option_3', 'option_4', 'correct_answer', 'image_link']
        self.supported_extensions = ['.png', '.jpg', '.jpeg']
        
    def determine_question_type(self, row):
        """
        Determine question type based on options and correct answer:
        - If only option_1 is filled and no correct_answer, it's a short answer
        - If all options are filled and has correct_answer, it's multiple choice
        """
        has_option_1 = pd.notna(row['option_1'])
        other_options_empty = all(pd.isna(row[f'option_{i}']) for i in range(2, 5))
        no_correct_answer = pd.isna(row['correct_answer'])
        
        if has_option_1 and other_options_empty and no_correct_answer:
            return 'short_answer'
        elif all(pd.notna(row[f'option_{i}']) for i in range(1, 5)) and pd.notna(row['correct_answer']):
            return 'multiple_choice'
        else:
            raise ValueError(f"Invalid question format in row with question: {row['question']}\n"
                           "For short answer: fill only option_1 and leave correct_answer empty\n"
                           "For multiple choice: fill all options and correct_answer")

    def validate_excel_format(self, df):
        """Validate if the Excel file has the correct format"""
        # Check if all required columns exist (except image_link which is optional)
        required_non_image = [col for col in self.required_columns if col != 'image_link']
        missing_columns = [col for col in required_non_image if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
        # Validate each row's format
        for idx, row in df.iterrows():
            try:
                question_type = self.determine_question_type(row)
                if question_type == 'multiple_choice':
                    if not 1 <= row['correct_answer'] <= 4:
                        raise ValueError(f"Invalid correct_answer value. Must be between 1-4. Found: {row['correct_answer']}")
            except ValueError as e:
                raise ValueError(f"Row {idx + 2}: {str(e)}")  # +2 because Excel rows start at 1 and have header

    def load_image(self, image_path):
        """Load and encode image if it exists"""
        if not image_path or pd.isna(image_path):
            return None

        image_path = str(image_path).strip()  # Ensure it's a string and remove spaces
        original_path = Path(image_path)

        # If no extension provided, try all supported extensions
        if not original_path.suffix:
            for ext in self.supported_extensions:
                test_path = Path("../resource/image") / f"{image_path}{ext}"
                if test_path.is_file():
                    resource_path = test_path
                    break
            else:  # No matching file found
                print(f"No image found with supported extensions for: {image_path}")
                return None
        else:
            # If extension is provided, verify it's supported
            if original_path.suffix.lower() not in self.supported_extensions:
                print(f"Unsupported image format: {original_path.suffix}. Supported formats: {', '.join(self.supported_extensions)}")
                return None
            resource_path = Path("../resource/image") / image_path

        # Ensure resource_path exists
        if not resource_path.is_file():
            print(f"Image not found: {resource_path}")
            return None

        try:
            with open(resource_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error loading image {resource_path}: {e}")
            return None

    def load_questions(self, file_path):
        """Load questions from Excel file and return in quiz format"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Add image_link column if it doesn't exist
            if 'image_link' not in df.columns:
                df['image_link'] = None
            
            # Validate format
            self.validate_excel_format(df)
            
            # Convert to quiz format
            questions = []
            for _, row in df.iterrows():
                image_data = self.load_image(row['image_link'])
                question_type = self.determine_question_type(row)
                
                question = {
                    "question": str(row['question']),
                    "type": question_type,
                    "image": image_data
                }
                
                if question_type == 'multiple_choice':
                    question.update({
                        "options": [
                            str(row['option_1']),
                            str(row['option_2']),
                            str(row['option_3']),
                            str(row['option_4'])
                        ],
                        "correct": int(row['correct_answer']) - 1  # Convert to 0-based index
                    })
                else:  # short_answer
                    question.update({
                        "answer": str(row['option_1']),  # Correct answer stored in option_1
                        "graded": False,
                        "score": None
                    })
                
                questions.append(question)
                
            return questions
            
        except Exception as e:
            raise Exception(f"Error loading questions: {str(e)}")
            
    def save_template(self, file_path):
        """Create a template Excel file"""
        template_data = {
            'question': [
                'What is 2 + 2?',
                'Which planet is closest to the Sun?',
                'Explain how photosynthesis works.'
            ],
            'option_1': ['3', 'Venus', 'Plants convert sunlight into energy through chlorophyll...'],
            'option_2': ['4', 'Mars', None],
            'option_3': ['5', 'Mercury', None],
            'option_4': ['6', 'Earth', None],
            'correct_answer': [2, 3, None],  # None for short answer
            'image_link': ['math.jpg', 'planets.jpg', 'photosynthesis.jpg']
        }
        
        df = pd.DataFrame(template_data)
        df.to_excel(file_path, index=False)