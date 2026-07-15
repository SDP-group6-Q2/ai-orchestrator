

def orchestrator_node(state: dict) -> dict:
    prompt = f"""
    For the user request "{state['request']}", create a JSON plan to address it.
    """
    plan = llm_planner.invoke([prompt])
    subtasks = [s.dict() for s in plan.subtasks]
    return {"plan": subtasks}