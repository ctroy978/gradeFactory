# GradeFactory

GradeFactory is a command-line application that streamlines the process of grading handwritten essays. It combines a multi-step workflow into a single, powerful tool that can:

1.  Process multi-page PDF files containing handwritten essays.
2.  Extract the text using Google Cloud Vision OCR.
3.  Correct OCR mistakes using the Gemini AI model.
4.  Grade the corrected essays using a multi-agent AI system powered by either Gemini or Grok.

## Features

-   **Unified CLI:** A single command-line interface with flags to control the workflow.
-   **Flexible Workflow:** Run the entire pipeline, or just the processing or grading steps independently.
-   **Multi-Model Support:** Choose between Google Gemini and Grok for the grading process.
-   **Standardized Structure:** Uses a clear and predictable folder structure for inputs and outputs.
-   **Automatic Naming:** Can automatically name the processed essay files based on the student's name in the text.

## Project Structure

```
gradefactory/
├── essays_to_grade/      # Output of the processing step, input for the grading step
├── graded_essays/        # Final output of the grading step
├── .env.example          # Example environment file
├── __init__.py
├── grading.py            # Contains the grading logic
├── main.py               # The main CLI entry point
├── processing.py         # Contains the OCR and text correction logic
├── prompts.py            # Stores all AI prompts
├── README.md             # This file
├── requirements.txt      # Project dependencies
└── utils.py              # Shared utility functions
```

## Setup and Installation

1.  **Prerequisites:**
    -   Python 3.10 or higher.
    -   A Google Cloud Platform account with the Vision API enabled.
    -   A `gen-lang-client.json` file with your Google Cloud service account credentials.

2.  **Clone or download the project.**

3.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set Up Environment Variables:**
    -   Copy the `.env.example` file to a new file named `.env`.
    -   Add your API keys to the `.env` file:
        ```
        GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
        XAI_API_KEY="YOUR_XAI_API_KEY"
        ```
    -   Make sure your `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set to the path of your `gen-lang-client.json` file, or place the `gen-lang-client.json` file in the root of the `gradefactory` directory.

## Usage

Because this application is structured as a Python package, you must run it as a module from the directory *above* `gradefactory`.

```bash
python -m gradefactory [FLAGS]
```

### Help

To see a full list of commands and flags, use the `--help` flag:

```bash
python -m gradefactory --help
```

### Examples

-   **Run the full pipeline (process and grade):**

    Place your raw multi-page PDF(s) in a folder (e.g., `my_raw_essays`).

    ```bash
    python -m gradefactory --full-pipeline --input-folder my_raw_essays --rubric path/to/my_rubric.json
    ```

-   **Run only the processing step:**

    ```bash
    python -m gradefactory --process --input-folder my_raw_essays --name
    ```
    *(The `--name` flag will attempt to name the output files based on the student's name.)*

-   **Run only the grading step (assuming you have already processed the essays):**

    ```bash
    python -m gradefactory --grade --rubric path/to/my_rubric.json --model grok
    ```
    *(This example uses the Grok model for grading.)*
