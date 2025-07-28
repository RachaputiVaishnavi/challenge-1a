This repository contains the solution for Round 2 of the Adobe India Hackathon 2025. The solution is divided into two sub-challenges:

1A. PDF Outline Extraction
1B. Persona-Based Content Relevance Ranking

This project is designed to process unstructured PDFs, extract their logical structure, and surface the most relevant content to a given user persona.

Problem Statements
Challenge 1A: PDF Outline Extraction
The goal is to develop a tool that takes a standard PDF document (such as a report, research paper, or proposal) and automatically extracts a structured outline of its contents. The output includes headings (e.g., H1, H2, H3), sub-sections, and associated page numbers in a hierarchical format.

The outline is generated using analysis of font size, font weight (e.g., bold), and layout positioning. The largest, boldest, and most visually distinct text is typically treated as high-level headings (H1), followed by lower-level subheadings (H2, H3, etc.).

The output is a JSON file that includes:

The document title

A list of sections with heading level, text, and page number

Challenge 1B: Persona-Based Content Relevance Ranking
The goal of this task is to identify and rank sections of one or more PDF documents based on their relevance to a specific user persona and task.

Given:

A user persona (e.g., HR manager, policy maker)

A task (e.g., draft a training plan, evaluate a proposal)

A set of PDFs

The system should:

Parse the PDFs and segment them into meaningful sections

Compute relevance scores using text similarity (e.g., TF-IDF, semantic embeddings)

Return the top-ranked sections along with:

Document name

Page number

Relevance score

Summary or text snippet

The output is a ranked JSON list of relevant content.

Technologies Used
Python 3

PyMuPDF (for PDF parsing)

Scikit-learn / Sentence Transformers (for NLP embeddings and similarity scoring)

JSON (for structured output)

Docker (for containerization and deployment)
