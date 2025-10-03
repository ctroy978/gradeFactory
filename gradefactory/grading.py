import os
import sys
import concurrent.futures
import requests

from .prompts import GRADING_PROMPT, MODERATOR_PROMPT
from .utils import get_rubric_data, extract_text_from_pdf, save_to_pdf

def get_evaluation(api_key, prompt, temperature, rubric_text, question, correct_answers, paper_text):
    """
    Gets evaluation from Grok model.
    """
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    question_text = f"Question:\n{question}\n\n" if question else ""
    answers_text = f"Correct Answers:\n" + "\n".join([f"- {ans}" for ans in correct_answers]) + "\n\n" if correct_answers else ""
    full_prompt = f"""Calibrate evaluations for community college freshmen: Be fair, constructive, and motivational. Typical papers should score 10-15/20, not failing unless severely deficient.\n\n{prompt}\n\n{question_text}{answers_text}Rubric:\n{rubric_text}\n\nStudent Paper:\n{paper_text}"""
    data = {"messages": [{"role": "user", "content": full_prompt}], "model": "grok-4-fast-reasoning", "stream": False, "temperature": temperature}
    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def moderate_evaluations(api_key, evaluation_a, evaluation_b, rubric_text, question, correct_answers, paper_text):
    """
    Moderates two evaluations using Grok.
    """
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    question_text = f"Question:\n{question}\n\n" if question else ""
    answers_text = f"Correct Answers:\n" + "\n".join([f"- {ans}" for ans in correct_answers]) + "\n\n" if correct_answers else ""
    prompt = f"""Calibrate evaluations for community college freshmen: Be fair, constructive, and motivational. Typical papers should score 10-15/20, not failing unless severely deficient.\n\n{MODERATOR_PROMPT}\n\n{question_text}{answers_text}Rubric:\n{rubric_text}\nStudent Paper:\n{paper_text}\nEvaluation from Grader A:\n{evaluation_a}\nEvaluation from Grader B:\n{evaluation_b}"""
    data = {"messages": [{"role": "user", "content": prompt}], "model": "grok-4-fast-reasoning", "stream": False, "temperature": 0.7}
    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def evaluate_paper(rubric_data, paper_text, xai_api_key):
    """
    Evaluates the student paper using a multi-agent system with Grok.
    rubric_data: dict with 'rubric', 'question', 'correct_answers'
    """
    try:
        rubric_text = rubric_data['rubric']
        question = rubric_data['question']
        correct_answers = rubric_data['correct_answers']
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if not xai_api_key:
                raise ValueError("XAI_API_KEY is required.")
            future_a = executor.submit(get_evaluation, xai_api_key, GRADING_PROMPT, 0.4, rubric_text, question, correct_answers, paper_text)
            future_b = executor.submit(get_evaluation, xai_api_key, GRADING_PROMPT, 0.8, rubric_text, question, correct_answers, paper_text)

            evaluation_a = future_a.result()
            evaluation_b = future_b.result()

        final_evaluation = moderate_evaluations(xai_api_key, evaluation_a, evaluation_b, rubric_text, question, correct_answers, paper_text)
        
        return evaluation_a, evaluation_b, final_evaluation

    except Exception as e:
        raise RuntimeError(f"Error during API call: {e}")

def run_grading(input_folder, output_folder, rubric_path, xai_api_key=None):
    """
    Evaluates a batch of papers in a folder using Grok.
    """
    print("--- Starting Grading Process ---")
    rubric_data = get_rubric_data(rubric_path)

    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder not found: {input_folder}")
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(".pdf"):
            paper_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            print(f"\nGrading {paper_path}...")

            try:
                paper_text = extract_text_from_pdf(paper_path)
                evaluation_a, evaluation_b, final_evaluation = evaluate_paper(rubric_data, paper_text, xai_api_key)

                evaluation_text = f"--- Agent 1 Evaluation ---\n{evaluation_a}\n--- End of Agent 1 Evaluation ---\n\n"
                evaluation_text += f"--- Agent 2 Evaluation ---\n{evaluation_b}\n--- End of Agent 2 Evaluation ---\n\n"
                evaluation_text += f"--- Final Moderator Evaluation ---\n{final_evaluation}\n--- End of Final Moderator Evaluation ---\n"

                save_to_pdf(evaluation_text, output_path)
                print(f"  - Saved evaluation to {output_path}")

            except Exception as e:
                print(f"Error evaluating {paper_path}: {e}", file=sys.stderr)
    print("\n--- Grading Process Complete ---")
