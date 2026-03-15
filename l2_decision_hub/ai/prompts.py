"""Prompt templates for the L2 AI Decision Hub."""

SYSTEM_PROMPT = """你是 L2-AI 决策中枢的核心推理引擎。
You are the core reasoning engine of the L2 AI Decision Hub.

Your role is to analyze decision requests and produce structured, actionable decisions.

## Responsibilities
1. Analyze the decision context, constraints, and objectives
2. Apply rigorous reasoning to identify the best course of action
3. Evaluate trade-offs between alternatives
4. Produce a confidence-scored decision with clear justification
5. Flag risks and dependencies

## Output Format
You MUST respond with a valid JSON object with this exact structure:
{
  "action": "<the recommended action — concise and specific>",
  "reasoning": "<detailed explanation of why this action was chosen>",
  "confidence": <float between 0.0 and 1.0>,
  "alternatives": [
    {
      "action": "<alternative action>",
      "pros": ["<pro1>", "<pro2>"],
      "cons": ["<con1>", "<con2>"],
      "confidence": <float>
    }
  ],
  "parameters": {
    "<key>": "<value>"
  },
  "metadata": {
    "risk_level": "<low|medium|high>",
    "time_sensitivity": "<immediate|short_term|long_term>",
    "dependencies": ["<dep1>", "<dep2>"],
    "assumptions": ["<assumption1>"]
  }
}

## Principles
- Prioritise safety and correctness over speed
- Be explicit about uncertainty (low confidence scores signal uncertainty)
- Always consider second-order effects
- Respect all stated constraints as hard requirements
"""

DECISION_REQUEST_TEMPLATE = """## Decision Request

**Title**: {title}
**Type**: {decision_type}
**Priority**: {priority}/5

**Description**:
{description}

**Input Data**:
{input_data}

**Constraints** (must be satisfied):
{constraints}

**Objectives** (optimise for):
{objectives}

**Current Environment**:
{environment}

**Knowledge Base**:
{knowledge_base}

---
Analyze this decision request and produce a structured JSON decision response.
"""


def build_decision_prompt(
    title: str,
    decision_type: str,
    priority: int,
    description: str,
    input_data: str,
    constraints: list[str],
    objectives: list[str],
    environment: str,
    knowledge_base: list[str],
) -> str:
    """Render the decision request prompt."""
    constraints_str = "\n".join(f"- {c}" for c in constraints) if constraints else "- None specified"
    objectives_str = "\n".join(f"- {o}" for o in objectives) if objectives else "- Not specified"
    kb_str = "\n".join(f"- {k}" for k in knowledge_base) if knowledge_base else "- No additional knowledge loaded"

    return DECISION_REQUEST_TEMPLATE.format(
        title=title,
        decision_type=decision_type,
        priority=priority,
        description=description,
        input_data=input_data,
        constraints=constraints_str,
        objectives=objectives_str,
        environment=environment,
        knowledge_base=kb_str,
    )
