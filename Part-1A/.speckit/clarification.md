# Clarifications

- **Q1: What is the format for task IDs?**
  - Resolution: Sequential positive integers starting at 1.
- **Q2: What happens when the storage file is missing?**
  - Resolution: Treat it as an empty task list and create the JSON file when the
    first task is saved.
