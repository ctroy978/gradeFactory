import os
import sys
import concurrent.futures
import requests
import google.generativeai as genai

from .prompts import GRADING_PROMPT, MODERATOR_PROMPT
from .utils import get_rubric_text, extract_text_from_pdf, save_to_pdf

def get_gemini_evaluation(prompt, temperature, rubric_text, paper_text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    full_prompt = f"""Calibrate evaluations for community college freshmen: Be fair, constructive, and motivational. Typical papers should score 10-15/20, not failing unless severely deficient.\n\n{prompt}\n\nRubric:\n{rubric_text}\n\nStudent Paper:\n{paper_text}"""
    response = model.generate_content(full_prompt, generation_config=genai.types.GenerationConfig(temperature=temperature))
    return response.text

def get_grok_evaluation(api_key, prompt, temperature, rubric_text, paper_text):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    full_prompt = f"""Calibrate evaluations for community college freshmen: Be fair, constructive, and motivational. Typical papers should score 10-15/20, not failing unless severely deficient.\n{prompt}\nRubric:\n{rubric_text}\nStudent Paper:\n{paper_text}"""
    data = {"messages": [{"role": "user", "content": full_prompt}], "model": "grok-4-fast-reasoning", "stream": False, "temperature": temperature}
    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def moderate_gemini_evaluations(evaluation_a, evaluation_b, rubric_text, paper_text):
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Calibrate evaluations for community college freshmen: Be fair, constructive, and motivational. Typical papers should score 10-15/20, not failing unless severely deficient.\n\n{MODERATOR_PROMPT}\n\nRubric:\n{rubric_text}\n\nStudent Paper:\n{paper_text}\n\nEvaluation from Grader A:\n{evaluation_a}\n\nEvaluation from Grader B:\n{evaluation_b}"""
    response = model.generate_content(prompt)
    return response.text

def moderate_grok_evaluations(api_key, evaluation_a, evaluation_b, rubric_text, paper_text):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    prompt = f"""Calibrate evaluations for community college freshmen: Be fair, constructive, and motivational. Typical papers should score 10-15/20, not failing unless severely deficient.\n{MODERATOR_PROMPT}\nRubric:\n{rubric_text}\nStudent Paper:\n{paper_text}\nEvaluation from Grader A:\n{evaluation_a}\nEvaluation from Grader B:\n{evaluation_b}"""
    data = {"messages": [{"role": "user", "content": prompt}], "model": "grok-4-fast-reasoning", "stream": False, "temperature": 0.7}
    response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=data)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def evaluate_paper(rubric_text, paper_text, model, xai_api_key=None):
    """
    Evaluates the student paper using a multi-agent system with the specified model.
    """
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            if model == 'gemini':
                future_a = executor.submit(get_gemini_evaluation, GRADING_PROMPT, 0.4, rubric_text, paper_text)
                future_b = executor.submit(get_gemini_evaluation, GRADING_PROMPT, 0.8, rubric_text, paper_text)
            elif model == 'grok':
                if not xai_api_key:
                    raise ValueError("XAI_API_KEY is required for Grok model.")
                future_a = executor.submit(get_grok_evaluation, xai_api_key, GRADING_PROMPT, 0.4, rubric_text, paper_text)
                future_b = executor.submit(get_grok_evaluation, xai_api_key, GRADING_PROMPT, 0.8, rubric_text, paper_text)
            else:
                raise ValueError(f"Unsupported model: {model}")

            evaluation_a = future_a.result()
            evaluation_b = future_b.result()

        if model == 'gemini':
            final_evaluation = moderate_gemini_evaluations(evaluation_a, evaluation_b, rubric_text, paper_text)
        else: # grok
            final_evaluation = moderate_grok_evaluations(xai_api_key, evaluation_a, evaluation_b, rubric_text, paper_text)
        
        return evaluation_a, evaluation_b, final_evaluation

    except Exception as e:
        raise RuntimeError(f"Error during API call: {e}")

def run_grading(input_folder, output_folder, rubric_path, model, xai_api_key=None):
    """
    Evaluates a batch of papers in a folder.
    """
    print("--- Starting Grading Process ---")
    rubric_text = get_rubric_text(rubric_path)

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
                evaluation_a, evaluation_b, final_evaluation = evaluate_paper(rubric_text, paper_text, model, xai_api_key)

                evaluation_text = f"--- Agent 1 Evaluation ---\n{evaluation_a}\n--- End of Agent 1 Evaluation ---\n\n"
                evaluation_text += f"--- Agent 2 Evaluation ---\n{evaluation_b}\n--- End of Agent 2 Evaluation ---\n\n"
                evaluation_text += f"--- Final Moderator Evaluation ---\n{final_evaluation}\n--- End of Final Moderator Evaluation ---\n"

                save_to_pdf(evaluation_text, output_path)
                print(f"  - Saved evaluation to {output_path}")

            except Exception as e:
                print(f"Error evaluating {paper_path}: {e}", file=sys.stderr)
    print("\n--- Grading Process Complete ---")
