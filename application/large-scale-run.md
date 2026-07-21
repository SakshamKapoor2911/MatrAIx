# Large-Scale Run — Representative Tasks × 1000 Personas

## The task

Run **all representative tasks** for the Large-scale run, listed in the
planning spreadsheet:

https://docs.google.com/spreadsheets/d/1CiXWXKKs9AxyqJbq1ZyBYqZj4-6RxRPPWzlB7zVzRyk/edit?gid=0#gid=0

Right now the scope is **rows 2-7**, but **rows 4, 5, and 6 are not
ready yet**.

All tasks live in the MatrAIx codebase:

https://github.com/MatrAIx-ai/MatrAIx

**Everything should be run on `main`.**

## Personas

Run each task with **1000 personas**, generated in **stratified mode**
from the task's own `persona_strategy.json`. Set `sampleSize` to `1000`
to request an exact total of 1000 personas. Do not also set
`sampleSizePerValueGroup`: the two fields are mutually exclusive, and
`sampleSizePerValueGroup` sets a quota for every stratum rather than an
exact total.

## Running

Run each task following the specification in the codebase. You will need
to specify what model to use.

## Where to find what you need to save

You need to know where to find the artifacts folder, and where to package
up the generated persona files. They are under `_generated`, and it is
better to package them before a clean-up for the next task.

## What to save

Save everything for each run to the HuggingFace dataset:

https://huggingface.co/datasets/MatrAIx2026/Demo_Application_Data/tree/main

Place the `modelname_taskname` folder inside the existing folder on the
dataset's main that matches the task's type (for example
`Type 1 - Survey/`, `Type 2 - Chatbot/`, `Type 3 - Website/`,
`Type 4 - App/`), using this structure:

```
folder: <type folder>/modelname_taskname
├── persona profile/          1000 personas automatically generated
│                             (stratified mode with sampleSize set to 1000),
│                             each persona has its own yaml file
├── artifact/                 all telemetries
├── report/                   (optional) reports generated
├── README                    a small description of the task and the
│                             configurations of the run
└── persona_strategy.json
```

**Final note:** upload everything generated to
[MatrAIx2026/Demo_Application_Data](https://huggingface.co/datasets/MatrAIx2026/Demo_Application_Data/tree/main)
on Hugging Face. Put each `modelname_taskname` folder under the matching task
type folder on the dataset's `main` branch (for example, `Type 1 - Survey/`,
`Type 2 - Chatbot/`, `Type 3 - Website/`, or `Type 4 - App/`).
