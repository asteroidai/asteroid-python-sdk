"""
Initializes and patches all supported LLM clients.
"""

def patch_all_clients():
    """
    Patches all supported LLM clients for monitoring.
    """
    from sentinel.wrappers.openai import patch_openai
    from sentinel.wrappers.anthropic import patch_anthropic
    from sentinel.wrappers.litellm import patch_litellm

    patch_openai()
    patch_anthropic()
    patch_litellm()
