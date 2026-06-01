---
title: The Workflow (how you actually use it)
description: 'Paste this into Claude (connected to Confluence): --- You are a resume
  optimization assistant helping Fernando Hernandez tailor his resume for a...'
ai_description: This page provides instructions for using a Claude-based resume tailoring
  system that matches a master resume against job descriptions.
date: '2026-04-06'
lastmod: '2026-04-06'
confluence_id: '965672963'
confluence_space: ITSAI
authors: []
tags: []
robots: index, follow
sitemap_exclude: false
---

# 🧠 1. MASTER PROMPT (Resume Tailor Engine)

Paste this into Claude (connected to Confluence):

---

## 🔹 PROMPT: Resume Tailoring Engine

```
You are a resume optimization assistant helping Fernando Hernandez tailor his resume for a specific role.

You have access to:
- A Master Resume
- A Bullet Point Bank
- A Skills Bank
- Past Tailored Resumes

Your job is to create a ONE-PAGE tailored resume by selecting and refining the most relevant content.

---

STEP 1: Analyze the Job Description
- Extract key responsibilities
- Identify required skills and tools
- Identify keywords and repeated themes
- Determine the role category (Product, Consulting, Data/AI, etc.)

---

STEP 2: Match Relevant Experience
- Select the most relevant experiences and projects
- Pull the strongest matching bullet points from the Bullet Point Bank
- Prioritize relevance over completeness

---

STEP 3: Optimize Bullet Points
- Start with strong action verbs
- Emphasize impact, outcomes, and contributions
- Keep language clear, concise, and professional
- Do NOT fabricate metrics or experiences
- Expand or refine wording only if needed

---

STEP 4: Skill Alignment
- Select skills that directly match the job description
- Prioritize tools, technical skills, and business-relevant capabilities

---

STEP 5: Output Requirements
- Keep resume to ONE PAGE
- Maintain clean formatting and consistency
- Ensure each bullet point is 1–2 lines max
- Focus on relevance, clarity, and impact

---

STEP 6: Provide Additional Insights
At the end, include:
1. Key keywords used from the job description
2. Any noticeable gaps in experience or skills
3. Suggestions for improving alignment in future applications

---

INPUTS:
[PASTE JOB DESCRIPTION]

[PASTE MASTER RESUME OR LINK CONFLUENCE PAGES]
```

---

# 🔄 2. WORKFLOW (how you ACTUALLY use it)

This is what makes your system efficient.

---

## ⚙️ Step-by-Step Flow

### 🟢 Step 1: Paste Job Description

- Drop it into Claude
- Run the **Master Prompt**

---

### 🟡 Step 2: Generate Tailored Resume

- Claude pulls from:
  
  - Bullet Bank
  - Skills Bank
  - Past resumes

👉 Output = your **first draft**

---

### 🔵 Step 3: Quick Human Edit (VERY IMPORTANT)

You:

- Fix wording if needed
- Adjust tone
- Remove anything that feels off

⏱ This should take ~2–5 minutes

---

### 🟣 Step 4: Save It Back to System

Create a new entry in:

## 📂 Past Tailored Versions Table

Include:

- Company
- Role
- Resume version
- Keywords used
- Notes (important)

---

# 📌 3. UPDATE SYSTEM (THIS is what makes it elite)

Without this, your system gets stale.

---

## 🔁 Weekly / Ongoing Update Loop

### 🧠 A. Add New Bullet Points

Whenever you:

- Finish a project
- Learn a tool
- Do something measurable

👉 Add to **Bullet Point Bank**

---

### 🛠 B. Refine Existing Bullets

If Claude rewrites something better:

👉 Replace the old version in your Bullet Bank  
 (THIS is how your system improves over time)

---

### 📊 C. Track What Works

Inside **Past Tailored Versions**, track:

- Did you get:
  
  - Interview?
  - Callback?
  - Rejection?

👉 Identify:

- Which bullets show up most in successful apps
- Which keywords matter most

---

### 🧩 D. Expand Skills Bank

When you notice repeated keywords like:

- “SQL”
- “stakeholder management”
- “Agile”

👉 Add them to Skills Bank (if relevant)

---

# 🔥 OPTIONAL (but VERY powerful)

## 🧠 “Auto-Update Prompt”

Run this weekly:

```
Analyze my recent tailored resumes and identify:

1. Most frequently used bullet points
2. Most in-demand skills across job descriptions
3. Any weak or underdeveloped areas in my experience
4. Suggestions for new bullet points I should add to my Bullet Bank

Use this to recommend improvements to my Resume Intelligence Engine.
```
