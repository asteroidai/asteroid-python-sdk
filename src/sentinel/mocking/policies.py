from enum import Enum

class MockPolicy(Enum):
    NO_MOCK = "no_mock"
    SAMPLE_LIST = "sample_from_list" # Sample from a list of responses
    SAMPLE_RANDOM = "sample_random" # Sample a random value from a specified type
    SAMPLE_LLM = "sample_llm" # Sample from an LLM with validation of output format
    SAMPLE_PREVIOUS_CALLS = "sample_from_previous_calls" # Sample from previous calls
    