---
chapter_number: 1
chapter_title: "<Title of Chapter>"
target_pages: 25
status: "planned" # planned | drafting | review | integrated
plan_file: "docs/superpowers/plans/ch01-plan.md"
paired_notebook: "notebooks/ch01.ipynb"

sections:
  - id: "sec01-01"
    title: "<Section Title>"
    type: "prose" # prose | notebook-paired | source-reformulation
    page_budget: 4
    labels:
      - "sec:ch01_intro"
    notation:
      - "\\theta"
      - "\\mathcal{D}"
    content_checklist:
      - "Define core intuition with everyday analogy"
      - "Establish formal mathematical notation"
      - "Connect with the running thread of parameter estimation"
    audits_required:
      - "spec-compliance"
      - "prose-quality"
      - "latex-macro-leak"
---

# Chapter 1 Design Plan

## Pedagogical Goal
Explain the core concepts introduced in this chapter and what the reader will be able to prove and compute by the end.

## Running Threads Tracked
- Thread A: Theoretical parameter estimation
- Thread B: Computational efficiency and scalability

## Section Breakdown
1. Section 1.1: Foundations and Motivation
2. Section 1.2: Mathematical Formulation
3. Section 1.3: Interactive Computational Verification (Paired Notebook)
