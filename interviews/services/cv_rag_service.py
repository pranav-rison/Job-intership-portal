"""
CV Interview RAG Service
Handles Resume processing, vector store creation, question generation, and answer evaluation
"""

import os
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple
from django.conf import settings
from groq import Groq
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate


class CVRAGService:
    """Service class for handling CV-based interview RAG pipeline"""
    
    def __init__(self):
        """Initialize the RAG service with Groq API and embeddings model"""
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        if not self.groq_api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        # Initialize Groq client
        self.groq_client = Groq(api_key=self.groq_api_key)
        
        # Initialize embeddings model (using HuggingFace sentence-transformers)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Initialize LangChain Groq LLM
        self.llm = ChatGroq(
            groq_api_key=self.groq_api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1024
        )
        
        # Set base path for vector stores
        self.vector_store_base_path = os.path.join(settings.MEDIA_ROOT, 'vector_stores')
        os.makedirs(self.vector_store_base_path, exist_ok=True)
    
    def process_resume(self, pdf_path: str, user_id: int) -> Tuple[str, int, str]:
        """
        Process uploaded PDF resume
        
        Args:
            pdf_path: Path to uploaded PDF file
            user_id: User ID for organizing vector stores
            
        Returns:
            Tuple of (extracted_text, total_chunks, vector_store_path)
        """
        try:
            # Load PDF using LangChain PyPDFLoader
            loader = PyPDFLoader(pdf_path)
            documents = loader.load()
            
            # Extract full text
            extracted_text = "\n\n".join([doc.page_content for doc in documents])
            
            # Split text into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)
            total_chunks = len(chunks)
            
            # Create FAISS vector store
            vector_store = FAISS.from_documents(chunks, self.embeddings)
            
            # Save vector store
            vector_store_path = os.path.join(
                self.vector_store_base_path,
                f"user_{user_id}_{Path(pdf_path).stem}"
            )
            vector_store.save_local(vector_store_path)
            
            return extracted_text, total_chunks, vector_store_path
            
        except Exception as e:
            raise Exception(f"Error processing resume: {str(e)}")
    
    def load_vector_store(self, vector_store_path: str) -> FAISS:
        """
        Load existing FAISS vector store
        
        Args:
            vector_store_path: Path to saved vector store
            
        Returns:
            FAISS vector store instance
        """
        try:
            vector_store = FAISS.load_local(
                vector_store_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            return vector_store
        except Exception as e:
            raise Exception(f"Error loading vector store: {str(e)}")
    
    def generate_question(self, vector_store_path: str, question_number: int) -> Dict[str, str]:
        """
        Generate interview question based on resume content using RAG
        
        Args:
            vector_store_path: Path to vector store
            question_number: Current question number
            
        Returns:
            Dict with 'question' and 'context'
        """
        try:
            # Load vector store
            vector_store = self.load_vector_store(vector_store_path)
            
            # Create retriever
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            
            # Define prompt template for question generation
            question_prompt = PromptTemplate(
                template="""You are an expert technical interviewer. Based on the candidate's resume information below, generate ONE insightful interview question that:
1. Tests their understanding of technologies/skills mentioned in their resume
2. Asks about their project experience or work history
3. Explores their problem-solving abilities related to their background

Resume Context:
{context}

Generate a clear, professional interview question (Question #{question_num}):""",
                input_variables=["context", "question_num"]
            )
            
            # Retrieve relevant context
            query = f"technical skills, projects, experience, education question {question_number}"
            relevant_docs = retriever.get_relevant_documents(query)
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
            
            # Generate question using Groq LLM
            prompt = question_prompt.format(context=context, question_num=question_number)
            
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.8,
                max_tokens=200
            )
            
            question = response.choices[0].message.content.strip()
            
            return {
                'question': question,
                'context': context
            }
            
        except Exception as e:
            raise Exception(f"Error generating question: {str(e)}")
    
    def evaluate_answer(
        self,
        vector_store_path: str,
        question: str,
        user_answer: str,
        question_context: str
    ) -> Dict:
        """
        Evaluate user's answer using RAG + Groq LLM
        
        Args:
            vector_store_path: Path to vector store
            question: The interview question
            user_answer: User's answer
            question_context: Original context used to generate question
            
        Returns:
            Dict with 'score', 'feedback', 'evaluation_details'
        """
        try:
            # Load vector store
            vector_store = self.load_vector_store(vector_store_path)
            
            # Retrieve relevant resume information
            retriever = vector_store.as_retriever(search_kwargs={"k": 3})
            relevant_docs = retriever.get_relevant_documents(user_answer)
            resume_context = "\n\n".join([doc.page_content for doc in relevant_docs])
            
            # Evaluation prompt
            eval_prompt = f"""You are an expert technical interviewer evaluating a candidate's answer.

Question: {question}

Candidate's Resume Context:
{question_context}

Candidate's Answer:
{user_answer}

Evaluate this answer on a scale of 0-20 based on:
1. Relevance to the question (0-5 points)
2. Technical accuracy and depth (0-7 points)
3. Communication clarity (0-4 points)
4. Real-world application/examples (0-4 points)

Provide:
- A numeric score (0-20)
- Detailed feedback (3-4 sentences)
- Key strengths and areas for improvement

Format your response as:
SCORE: [number]
FEEDBACK: [detailed feedback]
STRENGTHS: [key strengths]
IMPROVEMENTS: [areas to improve]"""

            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer providing constructive evaluation."},
                    {"role": "user", "content": eval_prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=500
            )
            
            evaluation_text = response.choices[0].message.content.strip()
            
            # Parse evaluation
            score = 0
            feedback = ""
            strengths = ""
            improvements = ""
            
            for line in evaluation_text.split('\n'):
                if line.startswith('SCORE:'):
                    try:
                        score = float(line.split(':')[1].strip())
                    except:
                        score = 10  # Default score if parsing fails
                elif line.startswith('FEEDBACK:'):
                    feedback = line.split(':', 1)[1].strip()
                elif line.startswith('STRENGTHS:'):
                    strengths = line.split(':', 1)[1].strip()
                elif line.startswith('IMPROVEMENTS:'):
                    improvements = line.split(':', 1)[1].strip()
            
            # If parsing didn't work, use the full text as feedback
            if not feedback:
                feedback = evaluation_text
            
            return {
                'score': min(max(score, 0), 20),  # Ensure score is between 0-20
                'feedback': feedback,
                'evaluation_details': {
                    'strengths': strengths,
                    'improvements': improvements,
                    'full_evaluation': evaluation_text
                }
            }
            
        except Exception as e:
            # Return default evaluation on error
            return {
                'score': 10,
                'feedback': f"Unable to evaluate answer automatically. Error: {str(e)}",
                'evaluation_details': {
                    'strengths': 'Answer provided',
                    'improvements': 'Please try again',
                    'full_evaluation': str(e)
                }
            }
    
    def generate_multiple_questions(
        self,
        vector_store_path: str,
        num_questions: int = 5
    ) -> List[Dict[str, str]]:
        """
        Generate multiple interview questions at once
        
        Args:
            vector_store_path: Path to vector store
            num_questions: Number of questions to generate
            
        Returns:
            List of dicts with 'question' and 'context'
        """
        questions = []
        for i in range(1, num_questions + 1):
            try:
                question_data = self.generate_question(vector_store_path, i)
                questions.append(question_data)
            except Exception as e:
                # If generation fails, add a fallback question
                questions.append({
                    'question': f"Tell me about your experience with the skills mentioned in your resume.",
                    'context': f"Fallback question {i}"
                })
        
        return questions
